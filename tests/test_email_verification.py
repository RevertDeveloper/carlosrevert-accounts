import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import EmailVerificationChallenge
from apps.authentication.services import (
    EmailVerificationDeliveryError,
    send_email_verification_code,
    verify_email_code,
)
from apps.users.models import User


class EmailVerificationTests(TestCase):
    def setUp(self):
        cache.clear()

    def _code_from_last_email(self) -> str:
        lines = (mail.outbox[-1].body or "").splitlines()
        return next(line.strip() for line in lines if re.fullmatch(r"[0-9]{6}", line.strip()))

    def _register_payload(self, email="ana@example.com") -> dict[str, object]:
        return {
            "username": "ana",
            "email": email,
            "password": "CorrectHorseBatteryStaple123!",
            "accepted_terms": True,
        }

    def test_api_register_sends_code_and_verify_logs_user_in(self):
        response = self.client.post(reverse("api-register"), self._register_payload())

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["authenticated"], False)
        self.assertTrue(response.json()["email_verification_required"])
        user = User.objects.get(email="ana@example.com")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        code = self._code_from_last_email()

        verified = self.client.post(
            reverse("api-verify-email"), {"email": user.email, "code": code}
        )

        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.json()["authenticated"])
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertTrue(self.client.get(reverse("api-me")).json()["user"]["email_verified"])

    def test_wrong_code_is_limited_and_valid_code_cannot_be_reused(self):
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        send_email_verification_code(user)
        code = self._code_from_last_email()

        for _ in range(5):
            self.assertIsNone(verify_email_code(user.email, "000000"))
        self.assertIsNone(verify_email_code(user.email, code))
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_resend_invalidates_previous_code_and_nonexistent_email_is_generic(self):
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        send_email_verification_code(user)
        old_code = self._code_from_last_email()

        response = self.client.post(reverse("api-resend-email-verification"), {"email": user.email})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            self.client.post(
                reverse("api-resend-email-verification"), {"email": user.email}
            ).status_code,
            202,
        )
        self.assertEqual(len(mail.outbox), 2)
        new_code = self._code_from_last_email()
        challenge = EmailVerificationChallenge.objects.get(user=user)
        self.assertFalse(check_password(old_code, challenge.code_hash))
        self.assertTrue(check_password(new_code, challenge.code_hash))
        self.assertEqual(
            self.client.post(
                reverse("api-resend-email-verification"), {"email": "missing@example.com"}
            ).status_code,
            202,
        )

    def test_expired_code_and_delivery_failure_do_not_verify_user(self):
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        send_email_verification_code(user)
        challenge = EmailVerificationChallenge.objects.get(user=user)
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=("expires_at",))
        self.assertIsNone(verify_email_code(user.email, self._code_from_last_email()))

        with patch("apps.authentication.services.send_mail", side_effect=RuntimeError("SMTP down")):
            with self.assertRaises(EmailVerificationDeliveryError):
                send_email_verification_code(user)
        user.refresh_from_db()
        self.assertFalse(user.email_verified)

    def test_api_login_rejects_unverified_user(self):
        User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )

        response = self.client.post(
            reverse("api-login"),
            {"identifier": "ana@example.com", "password": "CorrectHorseBatteryStaple123!"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_web_registration_redirects_to_verification_page(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "ana",
                "email": "ana@example.com",
                "password1": "CorrectHorseBatteryStaple123!",
                "password2": "CorrectHorseBatteryStaple123!",
                "accepted_terms": True,
            },
        )

        self.assertRedirects(response, reverse("email_verification"))
        self.assertContains(self.client.get(reverse("email_verification")), "Verifica tu correo")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_email_change_requires_new_verification(self):
        user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="CorrectHorseBatteryStaple123!",
            email_verified=True,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("account"),
            {"username": "ana", "email": "new@example.com", "first_name": "", "last_name": ""},
        )

        self.assertRedirects(response, reverse("email_verification"))
        user.refresh_from_db()
        self.assertEqual(user.email, "new@example.com")
        self.assertFalse(user.email_verified)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(
            self.client.post(
                reverse("email_verification"),
                {
                    "email": user.email,
                    "code": self._code_from_last_email(),
                },
            ).status_code,
            302,
        )
        user.refresh_from_db()
        self.assertTrue(user.email_verified)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_registration_delivery_failure_returns_service_unavailable_api(self):
        with patch("apps.authentication.services.send_mail", side_effect=RuntimeError("SMTP down")):
            response = self.client.post(reverse("api-register"), self._register_payload())

        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.get(email="ana@example.com").email_verified)
