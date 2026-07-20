import uuid

from django.test import TestCase
from django.urls import reverse

from apps.applications.models import ClientApplication
from apps.plans.models import Plan
from apps.plans.services import assign_plan
from apps.usage.models import DailyUsage, UsageEvent
from apps.users.models import User


class QuotaApiTests(TestCase):
    def setUp(self):
        Plan.objects.get_or_create(
            code="PREMIUM",
            defaults={"name": "Premium", "daily_interaction_limit": 20, "is_active": True},
        )
        self.user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.juridia = ClientApplication.objects.create(
            name="Juridia", slug="juridia", base_url="https://juridia.example"
        )
        self.clark = ClientApplication.objects.create(
            name="CLARK", slug="clark", base_url="https://clark.example"
        )
        self.client.force_login(self.user)

    def reserve(self, application="juridia", request_id=None):
        return self.client.post(
            reverse("api-usage-reserve"),
            {
                "application": application,
                "action": "legal_query",
                "request_id": str(request_id or uuid.uuid4()),
            },
        )

    def test_anonymous_user_cannot_reserve(self):
        self.client.logout()
        self.assertEqual(self.reserve().status_code, 403)

    def test_free_limit_shared_and_rejection_is_audited(self):
        for index in range(5):
            self.assertEqual(self.reserve("juridia" if index % 2 else "clark").status_code, 200)
        denied = self.reserve()
        self.assertEqual(denied.status_code, 429)
        self.assertEqual(denied.json()["code"], "daily_quota_exceeded")
        self.assertEqual(DailyUsage.objects.get(user=self.user).interaction_count, 5)
        self.assertTrue(
            UsageEvent.objects.filter(
                user=self.user, status=UsageEvent.Status.REJECTED_QUOTA
            ).exists()
        )

    def test_premium_has_twenty_interactions(self):
        assign_plan(self.user, "PREMIUM")
        for _ in range(20):
            self.assertEqual(self.reserve().status_code, 200)
        self.assertEqual(self.reserve().status_code, 429)

    def test_request_id_is_idempotent(self):
        request_id = uuid.uuid4()
        first = self.reserve(request_id=request_id)
        second = self.reserve(request_id=request_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(DailyUsage.objects.get(user=self.user).interaction_count, 1)

    def test_blocked_user_and_inactive_application_are_not_authorized(self):
        self.user.is_blocked = True
        self.user.save()
        self.assertEqual(self.reserve().status_code, 403)
        self.user.is_blocked = False
        self.user.save()
        self.juridia.is_active = False
        self.juridia.save()
        self.assertEqual(self.reserve().status_code, 403)
