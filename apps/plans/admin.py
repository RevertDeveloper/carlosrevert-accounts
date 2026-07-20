from django.contrib import admin

from .models import Plan, PlanChangeLog, UserPlan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "daily_interaction_limit", "is_active")
    list_editable = ("daily_interaction_limit", "is_active")
    search_fields = ("code", "name")


@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "assigned_at", "assigned_by")
    list_filter = ("plan",)
    search_fields = ("user__email", "user__username")


@admin.register(PlanChangeLog)
class PlanChangeLogAdmin(admin.ModelAdmin):
    list_display = ("user", "previous_plan", "new_plan", "changed_by", "created_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("user", "previous_plan", "new_plan", "changed_by", "reason", "created_at")
