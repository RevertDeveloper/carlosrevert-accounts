"""Vistas REST que exponen autenticación, cuota, integraciones internas y métricas."""

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.models import ClientApplication
from apps.authentication.services import (
    EmailVerificationDeliveryError,
    send_email_verification_code,
    verify_email_code,
)
from apps.usage.models import UsageEvent
from apps.usage.services.quota_service import (
    QuotaError,
    complete_interaction,
    fail_interaction,
    get_usage_summary,
    reserve_interaction,
    validate_interaction,
)
from apps.users.models import User

from .permissions import IsInternalService
from .rate_limit import is_rate_limited, is_rate_limited_identifier
from .serializers import (
    CompleteSerializer,
    FailSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResendEmailVerificationSerializer,
    ReserveSerializer,
    UsageEventSerializer,
    UserSerializer,
    ValidateReservationSerializer,
    VerifyEmailSerializer,
)


def quota_payload(summary) -> dict:  # type: ignore[no-untyped-def]
    """Convierte el objeto de cuota del dominio en la respuesta JSON pública."""
    return {
        "plan": summary.plan,
        "daily_limit": summary.daily_limit,
        "used_today": summary.used_today,
        "remaining_today": summary.remaining_today,
        "resets_at": summary.resets_at.isoformat(),
    }


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class CsrfView(APIView):
    """Entrega la cookie CSRF necesaria para clientes web basados en sesión."""

    permission_classes = (AllowAny,)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):  # type: ignore[no-untyped-def]
        return Response({"detail": "CSRF cookie set"})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class MeView(APIView):
    """Informa del estado de sesión actual sin exigir autenticación previa."""

    permission_classes = (AllowAny,)

    def get(self, request):  # type: ignore[no-untyped-def]
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": UserSerializer(request.user).data})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class RegisterView(APIView):
    """Crea una cuenta pendiente y desencadena la verificación de correo."""

    permission_classes = (AllowAny,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, "register", 5, 3600):
            return Response(
                {"detail": "Demasiados intentos de registro."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            send_email_verification_code(user)
        except EmailVerificationDeliveryError:
            return Response(
                {"detail": "La cuenta se ha creado, pero no se pudo enviar el código."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {
                "authenticated": False,
                "email_verification_required": True,
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(request=VerifyEmailSerializer, responses={200: OpenApiTypes.OBJECT})
class VerifyEmailView(APIView):
    """Verifica el código de correo e inicia la sesión de la cuenta validada."""

    permission_classes = (AllowAny,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, "verify-email", 10, 600):
            return Response(
                {"detail": "Demasiados intentos de verificación."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = verify_email_code(
            serializer.validated_data["email"], serializer.validated_data["code"]
        )
        if user is None:
            return Response(
                {"detail": "El código no es válido o ha caducado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user, backend="apps.authentication.backends.EmailOrUsernameModelBackend")
        return Response({"authenticated": True, "user": UserSerializer(user).data})


@extend_schema(request=ResendEmailVerificationSerializer, responses={202: OpenApiTypes.OBJECT})
class ResendEmailVerificationView(APIView):
    """Reenvía códigos sin revelar si el correo pertenece a una cuenta existente."""

    permission_classes = (AllowAny,)

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = ResendEmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        limited = (
            is_rate_limited(
                request,
                "email-verification-resend-ip",
                settings.EMAIL_VERIFICATION_RESEND_LIMIT,
                3600,
            )
            or is_rate_limited_identifier(
                "email-verification-resend-email",
                email,
                settings.EMAIL_VERIFICATION_RESEND_LIMIT,
                3600,
            )
            or is_rate_limited_identifier(
                "email-verification-resend-cooldown",
                email,
                1,
                settings.EMAIL_VERIFICATION_RESEND_INTERVAL_SECONDS,
            )
        )
        if not limited:
            user = User.objects.filter(
                email__iexact=email, is_active=True, is_blocked=False, email_verified=False
            ).first()
            if user is not None:
                try:
                    send_email_verification_code(user)
                except EmailVerificationDeliveryError:
                    pass
        return Response(
            {"detail": "Si existe una cuenta pendiente, recibirás un nuevo código."},
            status=status.HTTP_202_ACCEPTED,
        )


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class LoginView(APIView):
    """Autentica por usuario o correo con limitación de intentos."""

    permission_classes = (AllowAny,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, "login", 10, 900):
            return Response(
                {"detail": "Demasiados intentos de inicio de sesión."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Credenciales no válidas."}, status=status.HTTP_400_BAD_REQUEST
            )
        login(request, user, backend="apps.authentication.backends.EmailOrUsernameModelBackend")
        return Response({"authenticated": True, "user": UserSerializer(user).data})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class LogoutView(APIView):
    """Cierra la sesión autenticada actual."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):  # type: ignore[no-untyped-def]
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class UsageSummaryView(APIView):
    """Devuelve el estado de cuota de la cuenta autenticada."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):  # type: ignore[no-untyped-def]
        return Response(quota_payload(get_usage_summary(request.user)))


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class ReserveUsageView(APIView):
    """Reserva cuota para una acción antes de que el servicio de IA la procese."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, f"reserve:{request.user.pk}", 60, 60):
            return Response(
                {"detail": "Demasiadas reservas."}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        serializer = ReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.validated_data["application"]
        try:
            event, summary = reserve_interaction(
                request.user,
                application,
                serializer.validated_data["action"],
                serializer.validated_data["request_id"],
            )
        except QuotaError as exc:
            payload = {"authorized": False, "code": exc.code, "message": exc.message}
            if exc.code == "daily_quota_exceeded":
                payload.update(quota_payload(get_usage_summary(request.user)))
            return Response(payload, status=exc.http_status)
        return Response(
            {
                "authorized": event.status == UsageEvent.Status.AUTHORIZED,
                "request_id": str(event.request_id),
                **quota_payload(summary),
            }
        )


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class UsageHistoryView(APIView):
    """Lista exclusivamente los eventos de consumo de la cuenta autenticada."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):  # type: ignore[no-untyped-def]
        events = UsageEvent.objects.filter(user=request.user).select_related("application")
        if application := request.query_params.get("application"):
            events = events.filter(application__slug=application)
        if event_status := request.query_params.get("status"):
            events = events.filter(status=event_status)
        page = (
            self.paginator.paginate_queryset(events, request, view=self)
            if hasattr(self, "paginator")
            else None
        )
        if page is not None:
            return self.paginator.get_paginated_response(UsageEventSerializer(page, many=True).data)
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        result = paginator.paginate_queryset(events, request, view=self)
        return paginator.get_paginated_response(UsageEventSerializer(result, many=True).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class ApplicationsView(APIView):
    """Publica el catálogo de aplicaciones activas para el lanzador web."""

    permission_classes = (AllowAny,)

    def get(self, request):  # type: ignore[no-untyped-def]
        items = ClientApplication.objects.filter(is_active=True).values(
            "name", "slug", "base_url", "consumes_quota"
        )
        return Response(list(items))


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class CompleteUsageView(APIView):
    """Permite al backend interno marcar como completada su propia interacción."""

    permission_classes = (IsInternalService,)

    def post(self, request, request_id):  # type: ignore[no-untyped-def]
        serializer = CompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = UsageEvent.objects.filter(
            request_id=request_id, application=request.client_application
        ).first()
        if event is None:
            return Response(
                {"detail": "Interacción no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        event = complete_interaction(request_id, **serializer.validated_data)
        return Response(UsageEventSerializer(event).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class FailUsageView(APIView):
    """Permite al backend interno informar de un fallo de su interacción."""

    permission_classes = (IsInternalService,)

    def post(self, request, request_id):  # type: ignore[no-untyped-def]
        serializer = FailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = UsageEvent.objects.filter(
            request_id=request_id, application=request.client_application
        ).first()
        if event is None:
            return Response(
                {"detail": "Interacción no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        event = fail_interaction(request_id, **serializer.validated_data)
        return Response(UsageEventSerializer(event).data)


@extend_schema(request=ValidateReservationSerializer, responses={200: OpenApiTypes.OBJECT})
class ValidateUsageView(APIView):
    """Valida que una reserva pertenece al servicio interno que pretende consumirla."""

    permission_classes = (IsInternalService,)

    def post(self, request):  # type: ignore[no-untyped-def]
        serializer = ValidateReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["application"] != request.client_application.slug:
            return Response(
                {"valid": False, "code": "application_mismatch"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            event = validate_interaction(
                data["request_id"], request.client_application, data["action"]
            )
        except QuotaError as exc:
            return Response(
                {"valid": False, "code": exc.code, "message": exc.message},
                status=exc.http_status,
            )
        return Response(
            {
                "valid": True,
                "request_id": str(event.request_id),
                "user_id": event.user_id,
                "plan": event.user.user_plan.plan.code,
                "application": event.application.slug,
                "action": event.action,
            }
        )


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class MetricsView(APIView):
    """Devuelve métricas agregadas del día solo para personal administrador."""

    permission_classes = (IsAdminUser,)

    def get(self, request):  # type: ignore[no-untyped-def]
        from django.utils import timezone

        from apps.usage.models import DailyUsage
        from apps.users.models import User

        today = timezone.localdate()
        by_application = list(
            UsageEvent.objects.filter(created_at__date=today)
            .values("application__slug")
            .annotate(count=Count("id"))
            .order_by("application__slug")
        )
        errors = list(
            UsageEvent.objects.filter(created_at__date=today, status=UsageEvent.Status.FAILED)
            .values("application__slug")
            .annotate(count=Count("id"))
            .order_by("application__slug")
        )
        return Response(
            {
                "total_users": User.objects.count(),
                "free_users": User.objects.filter(user_plan__plan__code="FREE").count(),
                "premium_users": User.objects.filter(user_plan__plan__code="PREMIUM").count(),
                "active_users_today": DailyUsage.objects.filter(date=today, interaction_count__gt=0)
                .values("user_id")
                .distinct()
                .count(),
                "interactions_today": UsageEvent.objects.filter(
                    created_at__date=today,
                    status__in=[
                        UsageEvent.Status.AUTHORIZED,
                        UsageEvent.Status.PROCESSING,
                        UsageEvent.Status.COMPLETED,
                        UsageEvent.Status.FAILED,
                    ],
                ).count(),
                "interactions_by_application": by_application,
                "quota_rejections": UsageEvent.objects.filter(
                    created_at__date=today, status=UsageEvent.Status.REJECTED_QUOTA
                ).count(),
                "errors_by_application": errors,
            }
        )
