from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.users.models import User

from .models import EmailVerificationChallenge


class EmailVerificationDeliveryError(RuntimeError):
    """Raised when the verification message cannot be delivered."""


@dataclass(frozen=True)
class VerificationSettings:
    ttl_seconds: int = 600
    max_attempts: int = 5


def _verification_settings() -> VerificationSettings:
    return VerificationSettings(
        ttl_seconds=settings.EMAIL_VERIFICATION_CODE_TTL_SECONDS,
        max_attempts=settings.EMAIL_VERIFICATION_MAX_ATTEMPTS,
    )


def _new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _save_challenge(user: User, code: str, now) -> EmailVerificationChallenge:  # type: ignore[no-untyped-def]
    config = _verification_settings()
    challenge, _ = EmailVerificationChallenge.objects.select_for_update().get_or_create(
        user=user,
        defaults={
            "code_hash": make_password(code),
            "expires_at": now + timedelta(seconds=config.ttl_seconds),
            "sent_at": now,
        },
    )
    challenge.code_hash = make_password(code)
    challenge.expires_at = now + timedelta(seconds=config.ttl_seconds)
    challenge.attempts = 0
    challenge.sent_at = now
    challenge.consumed_at = None
    challenge.save(update_fields=("code_hash", "expires_at", "attempts", "sent_at", "consumed_at"))
    return challenge


def send_email_verification_code(user: User) -> None:
    """Replace the current challenge and send a fresh code without logging it."""
    code = _new_code()
    now = timezone.now()
    with transaction.atomic():
        _save_challenge(user, code, now)

    context = {
        "code": code,
        "expires_minutes": _verification_settings().ttl_seconds // 60,
        "user": user,
    }
    text_body = render_to_string("authentication/email_verification_code.txt", context)
    html_body = render_to_string("authentication/email_verification_code.html", context)
    try:
        message = EmailMultiAlternatives(
            subject="Código de verificación de Carlos Revert",
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001
        raise EmailVerificationDeliveryError from exc


def verify_email_code(email: str, code: str) -> User | None:
    """Consume a valid challenge and return the verified user."""
    user = User.objects.filter(
        email__iexact=email, is_active=True, is_blocked=False, email_verified=False
    ).first()
    if user is None:
        return None

    now = timezone.now()
    config = _verification_settings()
    with transaction.atomic():
        challenge = EmailVerificationChallenge.objects.select_for_update().filter(user=user).first()
        if (
            challenge is None
            or challenge.consumed_at is not None
            or challenge.expires_at <= now
            or challenge.attempts >= config.max_attempts
        ):
            return None

        challenge.attempts += 1
        valid = check_password(code, challenge.code_hash)
        if not valid:
            challenge.save(update_fields=("attempts",))
            return None

        challenge.consumed_at = now
        challenge.save(update_fields=("attempts", "consumed_at"))
        user.email_verified = True
        user.save(update_fields=("email_verified", "updated_at"))
    return user
