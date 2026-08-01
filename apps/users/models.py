from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("correo electrónico", unique=True)
    email_verified = models.BooleanField("correo verificado", default=False)
    is_blocked = models.BooleanField("bloqueado", default=False)
    accepted_terms_at = models.DateTimeField("términos aceptados el", null=True, blank=True)
    created_at = models.DateTimeField("creado el", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado el", auto_now=True)

    class Meta:
        ordering = ("-date_joined",)
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self) -> str:
        return self.email
