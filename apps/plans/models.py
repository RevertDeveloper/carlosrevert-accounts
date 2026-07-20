from django.conf import settings
from django.db import models


class Plan(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=80)
    daily_interaction_limit = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("daily_interaction_limit", "code")

    def __str__(self) -> str:
        return f"{self.name} ({self.daily_interaction_limit}/día)"


class UserPlan(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_plan"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="user_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_plans",
    )

    def __str__(self) -> str:
        return f"{self.user} - {self.plan.code}"


class PlanChangeLog(models.Model):  # noqa: DJ008
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plan_changes"
    )
    previous_plan = models.ForeignKey(
        Plan, null=True, on_delete=models.SET_NULL, related_name="previous_logs"
    )
    new_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="new_logs")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="plan_changes_made",
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
