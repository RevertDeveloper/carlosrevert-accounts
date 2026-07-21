import uuid

from django.conf import settings
from django.db import models


class DailyUsage(models.Model):  # noqa: DJ008
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_usages"
    )
    date = models.DateField()
    interaction_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("user", "date"), name="unique_daily_usage_per_user")
        ]
        ordering = ("-date",)


class UsageEvent(models.Model):  # noqa: DJ008
    class Status(models.TextChoices):
        AUTHORIZED = "authorized", "Authorized"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REJECTED_QUOTA = "rejected_quota", "Rejected by quota"
        REJECTED_AUTH = "rejected_auth", "Rejected by authentication"
        CANCELLED = "cancelled", "Cancelled"

    request_id = models.UUIDField(unique=True, default=uuid.uuid4)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_events"
    )
    application = models.ForeignKey(
        "applications.ClientApplication", on_delete=models.PROTECT, related_name="usage_events"
    )
    action = models.CharField(max_length=80)
    status = models.CharField(max_length=30, choices=Status.choices)
    interaction_cost = models.PositiveIntegerField(default=1)
    metadata = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("user", "created_at"), name="usage_usage_user_id_40f9db_idx"),
            models.Index(fields=("application", "status"), name="usage_app_status_idx"),
        ]


class InteractionReservation(models.Model):  # noqa: DJ008
    """Internal idempotency guard created before any quota increment."""

    request_id = models.UUIDField(unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey("applications.ClientApplication", on_delete=models.PROTECT)
    action = models.CharField(max_length=80)
    event = models.OneToOneField(
        UsageEvent, null=True, blank=True, on_delete=models.CASCADE, related_name="reservation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
