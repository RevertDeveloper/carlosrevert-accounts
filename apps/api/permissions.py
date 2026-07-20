import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.applications.models import ClientApplication


class IsInternalService(BasePermission):
    message = "Se requiere una credencial interna válida."

    def has_permission(self, request, view) -> bool:  # type: ignore[no-untyped-def]
        slug = request.headers.get("X-Application-Slug", "")
        key = request.headers.get("X-Service-Key", "")
        global_secret = request.headers.get("X-Internal-Service-Secret", "")
        application = ClientApplication.objects.filter(slug=slug, is_active=True).first()
        if application is None:
            return False
        matches_global = bool(settings.INTERNAL_SERVICE_SECRET) and secrets.compare_digest(
            global_secret, settings.INTERNAL_SERVICE_SECRET
        )
        if not (application.verifies_service_key(key) or matches_global):
            return False
        request.client_application = application
        return True
