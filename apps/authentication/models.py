from django.conf import settings
from django.db import models


class EmailVerificationChallenge(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_challenge",
        verbose_name="usuario",
    )
    code_hash = models.CharField("hash del código", max_length=128)
    expires_at = models.DateTimeField("expira el")
    attempts = models.PositiveSmallIntegerField("intentos", default=0)
    sent_at = models.DateTimeField("enviado el")
    consumed_at = models.DateTimeField("consumido el", null=True, blank=True)
    created_at = models.DateTimeField("creado el", auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "desafío de verificación de correo"
        verbose_name_plural = "desafíos de verificación de correo"

    def __str__(self) -> str:
        return f"Verificación de {self.user.email}"
