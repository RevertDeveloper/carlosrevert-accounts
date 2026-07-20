import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class ClientApplication(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    base_url = models.URLField()
    is_active = models.BooleanField(default=True)
    consumes_quota = models.BooleanField(default=True)
    service_key_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def rotate_service_key(self) -> str:
        key = secrets.token_urlsafe(32)
        self.service_key_hash = make_password(key)
        self.save(update_fields=("service_key_hash",))
        return key

    def verifies_service_key(self, key: str) -> bool:
        return bool(self.service_key_hash and check_password(key, self.service_key_hash))
