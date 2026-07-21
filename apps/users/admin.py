from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.plans.services import assign_plan

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "current_plan", "is_active", "is_blocked", "is_staff")
    list_filter = ("is_active", "is_blocked", "is_staff", "user_plan__plan")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
    actions = (
        "mark_premium",
        "mark_free",
        "block_users",
        "unblock_users",
        "deactivate_users",
        "activate_users",
    )

    def has_delete_permission(self, request, obj=None) -> bool:  # type: ignore[no-untyped-def]
        return False

    @admin.display(description="Plan")
    def current_plan(self, user: User) -> str:
        return (
            getattr(getattr(user, "user_plan", None), "plan", None).code
            if hasattr(user, "user_plan")
            else "-"
        )

    @admin.action(description="Marcar como PREMIUM")
    def mark_premium(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        for user in queryset:
            assign_plan(user, "PREMIUM", request.user, "Acción de administración")

    @admin.action(description="Marcar como FREE")
    def mark_free(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        for user in queryset:
            assign_plan(user, "FREE", request.user, "Acción de administración")

    @admin.action(description="Bloquear usuario")
    def block_users(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        queryset.update(is_blocked=True)

    @admin.action(description="Desbloquear usuario")
    def unblock_users(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        queryset.update(is_blocked=False)

    @admin.action(description="Desactivar usuario sin borrar su auditoría")
    def deactivate_users(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        queryset.update(is_active=False)

    @admin.action(description="Reactivar usuario")
    def activate_users(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        queryset.update(is_active=True)
