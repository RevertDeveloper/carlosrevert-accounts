"""Permiso que autentica los callbacks de los backends de IA por aplicación."""

from rest_framework.permissions import BasePermission

from apps.applications.models import ClientApplication


class IsInternalService(BasePermission):
    """Valida cabeceras de aplicación y clave de servicio, sin exponer credenciales."""

    message = "Se requiere una credencial interna válida."

    def has_permission(self, request, view) -> bool:  # type: ignore[no-untyped-def]
        """Asocia la aplicación autenticada a la petición cuando ambas cabeceras son válidas."""
        slug = request.headers.get("X-Application-Slug", "")
        key = request.headers.get("X-Service-Key", "")
        application = ClientApplication.objects.filter(slug=slug, is_active=True).first()
        if application is None:
            return False
        if not application.verifies_service_key(key):
            return False
        request.client_application = application
        return True
