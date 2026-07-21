from django.contrib import admin

from apps.admin import ReadOnlyAdminMixin

from .models import DailyUsage, InteractionReservation, UsageEvent


@admin.register(DailyUsage)
class DailyUsageAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("user", "date", "interaction_count", "updated_at")
    list_filter = ("date",)
    search_fields = ("user__email", "user__username")
    readonly_fields = ("user", "date", "interaction_count", "updated_at")


@admin.register(UsageEvent)
class UsageEventAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("request_id", "user", "application", "action", "status", "created_at")
    list_filter = ("status", "application")
    search_fields = ("request_id", "user__email", "action", "error_code")
    readonly_fields = (
        "request_id",
        "user",
        "application",
        "action",
        "status",
        "metadata",
        "error_code",
        "processing_time_ms",
        "validated_at",
        "created_at",
        "completed_at",
    )


@admin.register(InteractionReservation)
class InteractionReservationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("request_id", "user", "application", "action", "event", "created_at")
    readonly_fields = list_display
