"""Registro de aplicaciones cliente autorizadas a usar la plataforma de cuentas."""

import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models

APPLICATION_LAUNCHER_ORDER = ("home", "juridia", "clark", "transcriptor")


class ClientApplicationQuerySet(models.QuerySet):
    """Consultas específicas para mostrar las aplicaciones en el lanzador de cuenta."""

    def ordered_for_launcher(self):
        """Ordena las aplicaciones públicas según la prioridad definida por el producto."""
        launcher_order = models.Case(
            *(
                models.When(slug=slug, then=models.Value(position))
                for position, slug in enumerate(APPLICATION_LAUNCHER_ORDER)
            ),
            default=models.Value(len(APPLICATION_LAUNCHER_ORDER)),
            output_field=models.IntegerField(),
        )
        return self.annotate(_launcher_order=launcher_order).order_by("_launcher_order", "name")


class ClientApplication(models.Model):
    """Aplicación integrada, su URL pública y su credencial interna hasheada."""

    name = models.CharField("nombre", max_length=100)
    slug = models.SlugField("identificador", unique=True)
    base_url = models.URLField("URL base")
    is_active = models.BooleanField("activa", default=True)
    consumes_quota = models.BooleanField("consume cuota", default=True)
    service_key_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField("creada el", auto_now_add=True)

    objects = ClientApplicationQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        verbose_name = "aplicación cliente"
        verbose_name_plural = "aplicaciones cliente"

    def __str__(self) -> str:
        """Muestra el nombre de la aplicación en el administrador de Django."""
        return self.name

    @property
    def favicon_url(self) -> str:
        """Devuelve la ruta pública del favicon que utiliza el lanzador de aplicaciones."""
        if self.slug == "transcriptor":
            return "/static/favicon_io_cr/transcriptor.svg"
        favicon_name = {
            "home": "favicon.svg",
            "juridia": "apple-touch-icon.png",
        }.get(self.slug, "favicon.ico")
        return f"{self.base_url.rstrip('/')}/{favicon_name}"

    def rotate_service_key(self) -> str:
        """Genera una clave interna nueva y guarda únicamente su hash; devuelve la clave una vez."""
        key = secrets.token_urlsafe(32)
        self.service_key_hash = make_password(key)
        self.save(update_fields=("service_key_hash",))
        return key

    def verifies_service_key(self, key: str) -> bool:
        """Comprueba una clave interna recibida frente al hash almacenado."""
        return bool(self.service_key_hash and check_password(key, self.service_key_hash))
