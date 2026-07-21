from unittest.mock import patch

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.api.rate_limit import get_client_ip
from apps.plans.admin import PlanChangeLogAdmin, UserPlanAdmin
from apps.plans.models import PlanChangeLog, UserPlan
from apps.usage.admin import DailyUsageAdmin, InteractionReservationAdmin, UsageEventAdmin
from apps.usage.models import DailyUsage, InteractionReservation, UsageEvent
from apps.users.admin import CustomUserAdmin
from apps.users.models import User
from config.settings import production


class ProductionSettingsTests(SimpleTestCase):
    def test_security_settings_are_enabled(self):
        self.assertFalse(production.DEBUG)
        self.assertTrue(production.SECURE_SSL_REDIRECT)
        self.assertTrue(production.SESSION_COOKIE_SECURE)
        self.assertTrue(production.CSRF_COOKIE_SECURE)
        self.assertGreater(production.SECURE_HSTS_SECONDS, 0)
        self.assertEqual(production.EMAIL_BACKEND, "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual(
            production.CACHES["default"]["BACKEND"],
            "django.core.cache.backends.db.DatabaseCache",
        )


class ClientIpTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(TRUSTED_PROXY_IPS=["10.0.0.2"])
    def test_uses_last_forwarded_hop_only_for_trusted_proxy(self):
        request = self.factory.get(
            "/",
            REMOTE_ADDR="10.0.0.2",
            HTTP_X_FORWARDED_FOR="198.51.100.9, 203.0.113.7",
        )
        self.assertEqual(get_client_ip(request), "203.0.113.7")

    @override_settings(TRUSTED_PROXY_IPS=["10.0.0.2"])
    def test_ignores_spoofed_header_from_direct_client(self):
        request = self.factory.get(
            "/", REMOTE_ADDR="203.0.113.8", HTTP_X_FORWARDED_FOR="198.51.100.9"
        )
        self.assertEqual(get_client_ip(request), "203.0.113.8")


class OperationalHardeningTests(TestCase):
    def test_health_reports_database_failure(self):
        with patch("apps.dashboard.views.connection.cursor", side_effect=RuntimeError("down")):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unavailable")

    @patch("apps.authentication.views.is_rate_limited", return_value=True)
    def test_web_registration_is_rate_limited(self, _rate_limit):
        response = self.client.post(
            reverse("register"),
            {
                "username": "rate-limited",
                "email": "rate@example.test",
                "password1": "CorrectHorseBatteryStaple123!",
                "password2": "CorrectHorseBatteryStaple123!",
                "accepted_terms": True,
            },
        )
        self.assertEqual(response.status_code, 429)
        self.assertFalse(User.objects.filter(email="rate@example.test").exists())

    def test_audit_admins_are_read_only_and_users_cannot_be_deleted(self):
        factory = RequestFactory()
        get_request = factory.get("/admin/")
        post_request = factory.post("/admin/")
        user_admin = CustomUserAdmin(User, admin.site)
        self.assertFalse(user_admin.has_delete_permission(post_request))

        model_admins = (
            UserPlanAdmin(UserPlan, admin.site),
            PlanChangeLogAdmin(PlanChangeLog, admin.site),
            DailyUsageAdmin(DailyUsage, admin.site),
            UsageEventAdmin(UsageEvent, admin.site),
            InteractionReservationAdmin(InteractionReservation, admin.site),
        )
        for model_admin in model_admins:
            self.assertFalse(model_admin.has_add_permission(post_request))
            self.assertFalse(model_admin.has_delete_permission(post_request))
            self.assertFalse(model_admin.has_change_permission(post_request))
            self.assertTrue(model_admin.has_change_permission(get_request))
