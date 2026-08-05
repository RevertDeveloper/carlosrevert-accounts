"""Configuración de la aplicación Django que agrupa la capa REST."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Registra la aplicación API con una etiqueta estable para Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
    label = "api"
    verbose_name = "API"
