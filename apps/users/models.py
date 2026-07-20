from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField("correo electrónico", unique=True)
    email_verified = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date_joined",)

    def __str__(self) -> str:
        return self.email
