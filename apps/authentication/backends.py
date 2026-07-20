from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from apps.users.models import User


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(
        self, request, username: str | None = None, password: str | None = None, **kwargs
    ):  # type: ignore[no-untyped-def]
        identifier = username or kwargs.get("email")
        if not identifier or not password:
            return None
        user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        if user and user.is_active and not user.is_blocked and user.check_password(password):
            return user
        return None
