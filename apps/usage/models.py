"""Modelos que registran el consumo diario y el ciclo de vida de cada interacción."""

import uuid

from django.conf import settings
from django.db import models


class DailyUsage(models.Model):  # noqa: DJ008
    """Contador agregado por usuario y fecha, protegido por una restricción única."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_usages",
        verbose_name="usuario",
    )
    date = models.DateField("fecha")
    interaction_count = models.PositiveIntegerField("interacciones", default=0)
    updated_at = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        verbose_name = "uso diario"
        verbose_name_plural = "usos diarios"
        constraints = [
            models.UniqueConstraint(fields=("user", "date"), name="unique_daily_usage_per_user")
        ]
        ordering = ("-date",)


class UsageEvent(models.Model):  # noqa: DJ008
    """Evento auditable de una interacción autorizada, rechazada o finalizada."""

    class Status(models.TextChoices):
        AUTHORIZED = "authorized", "Autorizado"
        PROCESSING = "processing", "En proceso"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"
        REJECTED_QUOTA = "rejected_quota", "Rechazado por cuota"
        REJECTED_AUTH = "rejected_auth", "Rechazado por autenticación"
        CANCELLED = "cancelled", "Cancelado"

    request_id = models.UUIDField("ID de solicitud", unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_events",
        verbose_name="usuario",
    )
    application = models.ForeignKey(
        "applications.ClientApplication",
        on_delete=models.PROTECT,
        related_name="usage_events",
        verbose_name="aplicación",
    )
    action = models.CharField("acción", max_length=80)
    status = models.CharField("estado", max_length=30, choices=Status.choices)
    interaction_cost = models.PositiveIntegerField("coste de interacción", default=1)
    metadata = models.JSONField("metadatos", default=dict, blank=True)
    error_code = models.CharField("código de error", max_length=80, blank=True)
    processing_time_ms = models.PositiveIntegerField(
        "tiempo de proceso (ms)", null=True, blank=True
    )
    created_at = models.DateTimeField("creado el", auto_now_add=True)
    validated_at = models.DateTimeField("validado el", null=True, blank=True)
    completed_at = models.DateTimeField("completado el", null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "evento de consumo"
        verbose_name_plural = "eventos de consumo"
        indexes = [
            models.Index(fields=("user", "created_at"), name="usage_usage_user_id_40f9db_idx"),
            models.Index(fields=("application", "status"), name="usage_app_status_idx"),
        ]


class InteractionReservation(models.Model):  # noqa: DJ008
    """Guardia interna de idempotencia creada antes de incrementar la cuota."""

    request_id = models.UUIDField("ID de solicitud", unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="usuario"
    )
    application = models.ForeignKey(
        "applications.ClientApplication", on_delete=models.PROTECT, verbose_name="aplicación"
    )
    action = models.CharField(max_length=80)
    event = models.OneToOneField(
        UsageEvent,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="reservation",
        verbose_name="evento",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "reserva de interacción"
        verbose_name_plural = "reservas de interacción"
