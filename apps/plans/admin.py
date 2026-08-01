from django import forms
from django.contrib import admin

from apps.admin import ReadOnlyAdminMixin

from .models import Plan, PlanChangeLog, UserPlan
from .services import assign_plan


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "daily_interaction_limit", "is_active")
    list_editable = ("daily_interaction_limit", "is_active")
    search_fields = ("code", "name")


class UserPlanAdminForm(forms.ModelForm):
    plan = forms.ModelChoiceField(
        label="Plan nuevo",
        queryset=Plan.objects.filter(is_active=True),
        help_text="Selecciona el plan configurado que tendrá este usuario.",
    )

    class Meta:
        model = UserPlan
        fields = ("plan",)


@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    form = UserPlanAdminForm
    list_display = ("user", "plan", "assigned_at", "assigned_by")
    list_filter = ("plan",)
    search_fields = ("user__email", "user__username")
    readonly_fields = ("user", "assigned_at", "updated_at", "assigned_by")

    def has_add_permission(self, request) -> bool:  # type: ignore[no-untyped-def]
        return False

    def has_delete_permission(self, request, obj=None) -> bool:  # type: ignore[no-untyped-def]
        return False

    def save_model(self, request, obj, form, change) -> None:  # type: ignore[no-untyped-def]
        selected_plan = form.cleaned_data["plan"]
        assign_plan(
            obj.user,
            selected_plan.code,
            request.user,
            "Cambio desde asignaciones de planes en el panel de administración",
        )
        obj.refresh_from_db()


@admin.register(PlanChangeLog)
class PlanChangeLogAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("user", "previous_plan", "new_plan", "changed_by", "created_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("user", "previous_plan", "new_plan", "changed_by", "reason", "created_at")
