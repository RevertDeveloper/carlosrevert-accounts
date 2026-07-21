from rest_framework.permissions import BasePermission

from apps.applications.models import ClientApplication


class IsInternalService(BasePermission):
    message = "Se requiere una credencial interna válida."

    def has_permission(self, request, view) -> bool:  # type: ignore[no-untyped-def]
        slug = request.headers.get("X-Application-Slug", "")
        key = request.headers.get("X-Service-Key", "")
        application = ClientApplication.objects.filter(slug=slug, is_active=True).first()
        if application is None:
            return False
        if not application.verifies_service_key(key):
            return False
        request.client_application = application
        return True
