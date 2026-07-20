from django.contrib import admin, messages

from .models import ClientApplication


@admin.register(ClientApplication)
class ClientApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "base_url", "is_active", "consumes_quota")
    list_filter = ("is_active", "consumes_quota")
    search_fields = ("name", "slug")
    actions = ("rotate_keys",)

    @admin.action(description="Rotar credencial de servicio")
    def rotate_keys(self, request, queryset) -> None:  # type: ignore[no-untyped-def]
        for application in queryset:
            key = application.rotate_service_key()
            self.message_user(
                request, f"Nueva clave para {application.slug}: {key}", messages.WARNING
            )
