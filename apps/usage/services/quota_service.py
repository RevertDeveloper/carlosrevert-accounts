"""Operaciones transaccionales e idempotentes del consumo de cuota."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.plans.models import UserPlan

from ..models import DailyUsage, InteractionReservation, UsageEvent

if TYPE_CHECKING:
    from apps.applications.models import ClientApplication
    from apps.users.models import User


class QuotaError(Exception):
    """Error de dominio que conserva el código y estado HTTP que debe devolver la API."""

    def __init__(self, code: str, message: str, http_status: int = 403) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


@dataclass(frozen=True)
class QuotaStatus:
    """Resumen inmutable de la cuota disponible para una cuenta en el día actual."""

    plan: str
    daily_limit: int
    used_today: int
    remaining_today: int
    resets_at: datetime


def _today() -> date:
    """Devuelve la fecha local configurada por Django para agrupar el consumo diario."""
    return timezone.localdate()


def _resets_at() -> datetime:
    """Calcula el inicio del siguiente día local, momento en que se reinicia la cuota."""
    tomorrow = _today() + timedelta(days=1)
    return timezone.make_aware(datetime.combine(tomorrow, time.min))


def _clean_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Elimina prompts, respuestas y otros cuerpos potencialmente sensibles."""
    if not metadata:
        return {}
    forbidden = {
        "prompt",
        "prompts",
        "response",
        "responses",
        "input",
        "output",
        "content",
        "message",
    }
    clean = {
        str(key): value for key, value in metadata.items() if str(key).lower() not in forbidden
    }
    return clean if len(str(clean)) <= 4096 else {"metadata_truncated": True}


def _assignment_for(user: "User") -> UserPlan:
    """Obtiene el plan asignado al usuario o informa de una configuración incompleta."""
    try:
        return UserPlan.objects.select_related("plan").get(user=user)
    except UserPlan.DoesNotExist as exc:
        raise QuotaError("plan_not_assigned", "La cuenta no tiene un plan asignado.") from exc


def _locked_usage(user: "User") -> DailyUsage:
    """Obtiene y bloquea el contador diario, creándolo de forma segura si no existe."""
    today = _today()
    try:
        return DailyUsage.objects.select_for_update().get(user=user, date=today)
    except DailyUsage.DoesNotExist:
        try:
            with transaction.atomic():
                DailyUsage.objects.create(user=user, date=today)
        except IntegrityError:
            pass
        return DailyUsage.objects.select_for_update().get(user=user, date=today)


def _status_from(assignment: UserPlan, used: int) -> QuotaStatus:
    """Construye el resumen de cuota a partir del plan y las interacciones consumidas."""
    limit = assignment.plan.daily_interaction_limit
    return QuotaStatus(assignment.plan.code, limit, used, max(0, limit - used), _resets_at())


def check_quota(user: "User") -> QuotaStatus:
    """Consulta la cuota sin modificarla y valida que la cuenta pueda consumirla."""
    if not user.is_authenticated:
        raise QuotaError("authentication_required", "Debes iniciar sesión.", 401)
    if not user.is_active or user.is_blocked:
        raise QuotaError("account_unavailable", "Tu cuenta no puede consumir interacciones.")
    assignment = _assignment_for(user)
    usage = DailyUsage.objects.filter(user=user, date=_today()).only("interaction_count").first()
    return _status_from(assignment, usage.interaction_count if usage else 0)


def reserve_interaction(
    user: "User", application: "ClientApplication", action: str, request_id: Any
) -> tuple[UsageEvent, QuotaStatus]:
    """Reserva una interacción atómicamente; repetir el ID devuelve el resultado original."""
    quota_error: QuotaError | None = None
    with transaction.atomic():
        try:
            with transaction.atomic():
                reservation = InteractionReservation.objects.create(
                    request_id=request_id, user=user, application=application, action=action
                )
        except IntegrityError:
            # Solo se bloquea la reserva: PostgreSQL no puede aplicar FOR UPDATE
            # sobre el lado anulable que introduce select_related("event").
            reservation = InteractionReservation.objects.select_for_update().get(
                request_id=request_id
            )
            if (
                reservation.user_id != user.id
                or reservation.application_id != application.id
                or reservation.action != action
            ):
                raise QuotaError(
                    "request_id_conflict", "El request_id ya pertenece a otra interacción.", 409
                ) from None
            if reservation.event is None:
                raise QuotaError(
                    "request_in_progress", "La interacción sigue en curso.", 409
                ) from None
            if reservation.event.status != UsageEvent.Status.AUTHORIZED:
                raise QuotaError(
                    "request_already_used", "La interacción ya ha sido procesada.", 409
                ) from None
            return reservation.event, check_quota(user)

        if not user.is_active or user.is_blocked:
            event = UsageEvent.objects.create(
                request_id=request_id,
                user=user,
                application=application,
                action=action,
                status=UsageEvent.Status.REJECTED_AUTH,
            )
            reservation.event = event
            reservation.save(update_fields=("event",))
            quota_error = QuotaError(
                "account_unavailable", "Tu cuenta no puede consumir interacciones."
            )
            status = QuotaStatus("", 0, 0, 0, _resets_at())
        elif not application.is_active:
            event = UsageEvent.objects.create(
                request_id=request_id,
                user=user,
                application=application,
                action=action,
                status=UsageEvent.Status.REJECTED_AUTH,
                error_code="application_inactive",
            )
            reservation.event = event
            reservation.save(update_fields=("event",))
            quota_error = QuotaError("application_inactive", "La aplicación no está disponible.")
            status = check_quota(user)
        else:
            assignment = _assignment_for(user)
            usage = _locked_usage(user)
            status = _status_from(assignment, usage.interaction_count)
            if application.consumes_quota and status.remaining_today < 1:
                event = UsageEvent.objects.create(
                    request_id=request_id,
                    user=user,
                    application=application,
                    action=action,
                    status=UsageEvent.Status.REJECTED_QUOTA,
                )
                reservation.event = event
                reservation.save(update_fields=("event",))
                quota_error = QuotaError(
                    "daily_quota_exceeded", "Has alcanzado el límite diario de interacciones.", 429
                )
            else:
                if application.consumes_quota:
                    usage.interaction_count += 1
                    usage.save(update_fields=("interaction_count", "updated_at"))
                    status = _status_from(assignment, usage.interaction_count)
                event = UsageEvent.objects.create(
                    request_id=request_id,
                    user=user,
                    application=application,
                    action=action,
                    status=UsageEvent.Status.AUTHORIZED,
                )
                reservation.event = event
                reservation.save(update_fields=("event",))
    if quota_error:
        raise quota_error
    return event, status


@transaction.atomic
def validate_interaction(
    request_id: Any,
    application: "ClientApplication",
    action: str,
) -> UsageEvent:
    """Valida una reserva una única vez antes de iniciar trabajo de IA en el cliente."""
    try:
        event = (
            UsageEvent.objects.select_for_update()
            .select_related("user", "application")
            .get(request_id=request_id)
        )
    except UsageEvent.DoesNotExist as exc:
        raise QuotaError("invalid_reservation", "La reserva no existe.", 404) from exc

    if event.application_id != application.id or event.action != action:
        raise QuotaError(
            "reservation_mismatch", "La reserva no corresponde a esta aplicación o acción.", 403
        )
    if event.status != UsageEvent.Status.AUTHORIZED:
        raise QuotaError("request_already_used", "La reserva ya ha sido utilizada.", 409)
    if not event.user.is_active or event.user.is_blocked or not application.is_active:
        raise QuotaError("account_unavailable", "La cuenta o aplicación no está disponible.", 403)

    event.status = UsageEvent.Status.PROCESSING
    event.validated_at = timezone.now()
    event.save(update_fields=("status", "validated_at"))
    return event


@transaction.atomic
def complete_interaction(
    request_id: Any, metadata: dict[str, Any] | None = None, processing_time_ms: int | None = None
) -> UsageEvent:
    """Marca una interacción en proceso como completada y conserva metadatos seguros."""
    event = UsageEvent.objects.select_for_update().get(request_id=request_id)
    if event.status == UsageEvent.Status.PROCESSING:
        event.status = UsageEvent.Status.COMPLETED
        event.metadata = _clean_metadata(metadata)
        event.processing_time_ms = processing_time_ms
        event.completed_at = timezone.now()
        event.save(update_fields=("status", "metadata", "processing_time_ms", "completed_at"))
    return event


@transaction.atomic
def fail_interaction(
    request_id: Any, error_code: str, metadata: dict[str, Any] | None = None
) -> UsageEvent:
    """Marca una interacción como fallida y devuelve cuota en los errores recuperables."""
    event = (
        UsageEvent.objects.select_for_update()
        .select_related("application", "user")
        .get(request_id=request_id)
    )
    if event.status != UsageEvent.Status.PROCESSING:
        return event
    event.status = UsageEvent.Status.FAILED
    event.error_code = error_code[:80]
    event.metadata = _clean_metadata(metadata)
    event.completed_at = timezone.now()
    event.save(update_fields=("status", "error_code", "metadata", "completed_at"))
    if event.application.consumes_quota and error_code in settings.QUOTA_REFUNDABLE_ERROR_CODES:
        usage = _locked_usage(event.user)
        if usage.interaction_count:
            usage.interaction_count -= 1
            usage.save(update_fields=("interaction_count", "updated_at"))
    return event


def get_usage_summary(user: "User") -> QuotaStatus:
    """Expone el resumen de cuota para las capas web y API."""
    return check_quota(user)
