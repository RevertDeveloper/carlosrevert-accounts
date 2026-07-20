import uuid

from django.test import TestCase
from django.urls import reverse

from apps.applications.models import ClientApplication
from apps.usage.models import UsageEvent
from apps.users.models import User


class ApiPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.other = User.objects.create_user(
            username="bea", email="bea@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.application = ClientApplication.objects.create(
            name="Juridia", slug="juridia", base_url="https://juridia.example"
        )

    def test_history_is_scoped_to_authenticated_user(self):
        UsageEvent.objects.create(
            request_id=uuid.uuid4(),
            user=self.other,
            application=self.application,
            action="query",
            status="completed",
        )
        self.client.force_login(self.user)
        data = self.client.get(reverse("api-usage-history")).json()
        self.assertEqual(data["count"], 0)

    def test_metrics_requires_staff(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("api-metrics")).status_code, 403)

    def test_internal_callback_rejects_invalid_and_accepts_application_key(self):
        event = UsageEvent.objects.create(
            request_id=uuid.uuid4(),
            user=self.user,
            application=self.application,
            action="query",
            status="authorized",
        )
        url = reverse("api-usage-complete", args=[event.request_id])
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        key = self.application.rotate_service_key()
        response = self.client.post(
            url,
            {"processing_time_ms": 12},
            HTTP_X_APPLICATION_SLUG="juridia",
            HTTP_X_SERVICE_KEY=key,
        )
        self.assertEqual(response.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.status, "completed")
