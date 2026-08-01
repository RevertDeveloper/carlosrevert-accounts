from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm

from apps.plans.models import Plan
from apps.plans.services import assign_plan

from .models import User


class UserAdminForm(UserChangeForm):
    plan = forms.ModelChoiceField(
        label="Plan",
        queryset=Plan.objects.filter(is_active=True),
        required=False,
        help_text="Selecciona el plan activo que tendrá este usuario.",
    )

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            assignment = getattr(self.instance, "user_plan", None)
            if assignment:
                self.initial["plan"] = assignment.plan_id
        labels = {
            "username": "Usuario",
            "password": "Contraseña",
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "is_active": "Cuenta activa",
            "email_verified": "Correo verificado",
            "is_blocked": "Cuenta bloqueada",
            "is_staff": "Acceso al administrador",
            "is_superuser": "Superusuario",
            "groups": "Grupos",
            "user_permissions": "Permisos específicos",
        }
        for name, label in labels.items():
            if name in self.fields:
                self.fields[name].label = label


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserAdminForm
    list_display = (
        "username",
        "email",
        "current_plan",
        "active_status",
        "email_verified_status",
        "blocked_status",
        "staff_status",
    )
    list_filter = ("is_active", "email_verified", "is_blocked", "is_staff", "user_plan__plan")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "email")}),
        (
            "Plan y acceso",
            {
                "fields": (
                    "plan",
                    "is_active",
                    "email_verified",
                    "is_blocked",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        ("Permisos", {"fields": ("groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            "Datos de acceso",
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "plan"),
            },
        ),
        ("Permisos", {"fields": ("is_staff", "is_active")}),
    )
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

    @admin.display(description="Cuenta activa", boolean=True)
    def active_status(self, user: User) -> bool:
        return user.is_active

    @admin.display(description="Correo verificado", boolean=True)
    def email_verified_status(self, user: User) -> bool:
        return user.email_verified

    @admin.display(description="Cuenta bloqueada", boolean=True)
    def blocked_status(self, user: User) -> bool:
        return user.is_blocked

    @admin.display(description="Acceso al administrador", boolean=True)
    def staff_status(self, user: User) -> bool:
        return user.is_staff

    @admin.display(description="Plan actual")
    def current_plan(self, user: User) -> str:
        return (
            getattr(getattr(user, "user_plan", None), "plan", None).code
            if hasattr(user, "user_plan")
            else "-"
        )

    def save_model(self, request, obj, form, change) -> None:  # type: ignore[no-untyped-def]
        super().save_model(request, obj, form, change)
        selected_plan = form.cleaned_data.get("plan")
        if selected_plan:
            assign_plan(
                obj,
                selected_plan.code,
                request.user,
                "Asignación desde el panel de administración",
            )

    @admin.action(description="Marcar como PREMIUM")
    def mark_premium(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        for user in queryset:
            assign_plan(user, "PREMIUM", request.user, "Acción de administración")

    @admin.action(description="Marcar como Acceso de demostración")
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
