"""Modelos de planes, su asignación a cuentas y su trazabilidad administrativa."""

from django.conf import settings
from django.db import models


class Plan(models.Model):
    """Define un plan configurable y su límite diario de interacciones."""

    code = models.CharField("código", max_length=30, unique=True)
    name = models.CharField("nombre", max_length=80)
    daily_interaction_limit = models.PositiveIntegerField("límite diario de interacciones")
    is_active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField("creado el", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        ordering = ("daily_interaction_limit", "code")
        verbose_name = "plan"
        verbose_name_plural = "planes"

    def __str__(self) -> str:
        return f"{self.name} ({self.daily_interaction_limit}/día)"


class UserPlan(models.Model):
    """Relaciona de forma única cada usuario con el plan que tiene asignado."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_plan",
        verbose_name="usuario",
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="user_assignments", verbose_name="plan"
    )
    assigned_at = models.DateTimeField("asignado el", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_plans",
        verbose_name="asignado por",
    )

    class Meta:
        verbose_name = "asignación de plan"
        verbose_name_plural = "asignaciones de planes"

    def __str__(self) -> str:
        return f"{self.user} - {self.plan.code}"


class PlanChangeLog(models.Model):  # noqa: DJ008
    """Audita cada cambio de plan, incluido el administrador y su motivo."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="plan_changes",
        verbose_name="usuario",
    )
    previous_plan = models.ForeignKey(
        Plan,
        null=True,
        on_delete=models.SET_NULL,
        related_name="previous_logs",
        verbose_name="plan anterior",
    )
    new_plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="new_logs", verbose_name="plan nuevo"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="plan_changes_made",
        verbose_name="cambiado por",
    )
    reason = models.CharField("motivo", max_length=255, blank=True)
    created_at = models.DateTimeField("creado el", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "historial de cambio de plan"
        verbose_name_plural = "historial de cambios de plan"
