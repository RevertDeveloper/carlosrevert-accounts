import tempfile
import uuid
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.applications.models import ClientApplication
from apps.plans.models import Plan, PlanChangeLog
from apps.plans.services import assign_plan
from apps.usage.models import DailyUsage, UsageEvent
from apps.usage.services.quota_service import (
    QuotaError,
    check_quota,
    complete_interaction,
    fail_interaction,
    reserve_interaction,
    validate_interaction,
)
from apps.users.models import User


class ManagementCommandTests(TestCase):
    def test_seed_commands_and_demo_users_are_idempotent(self):
        call_command("seed_plans")
        call_command("seed_plans")
        call_command("seed_applications")
        call_command("seed_applications")
        call_command("create_demo_users")
        call_command("create_demo_users")
        self.assertEqual(Plan.objects.get(code="FREE").daily_interaction_limit, 5)
        self.assertEqual(Plan.objects.get(code="PREMIUM").daily_interaction_limit, 20)
        self.assertEqual(ClientApplication.objects.count(), 4)
        self.assertTrue(User.objects.filter(username="demo-admin", is_superuser=True).exists())

    def test_keycloak_import_is_idempotent_and_never_imports_passwords(self):
        source = Path(tempfile.mkstemp(suffix=".csv")[1])
        self.addCleanup(source.unlink)
        source.write_text(
            "username,email,first_name,last_name\nlegacy,legacy@example.test,Ana,Legacy\ninvalid,,X,Y\n"
        )
        call_command("import_keycloak_users", str(source))
        call_command("import_keycloak_users", str(source))
        user = User.objects.get(username="legacy")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(User.objects.filter(username="legacy").count(), 1)


class QuotaServiceTests(TestCase):
    def setUp(self):
        call_command("seed_plans")
        self.user = User.objects.create_user(
            username="service",
            email="service@example.test",
            password="CorrectHorseBatteryStaple123!",
        )
        self.application = ClientApplication.objects.create(
            name="Juridia", slug="juridia", base_url="https://juridia.example"
        )

    def test_completion_sanitizes_content_and_refundable_failure_decrements(self):
        event, _ = reserve_interaction(self.user, self.application, "query", uuid.uuid4())
        validate_interaction(event.request_id, self.application, "query")
        complete_interaction(event.request_id, {"prompt": "secret", "source": "juridia"}, 5)
        event.refresh_from_db()
        self.assertEqual(event.status, UsageEvent.Status.COMPLETED)
        self.assertEqual(event.metadata, {"source": "juridia"})

        retry, _ = reserve_interaction(self.user, self.application, "query", uuid.uuid4())
        validate_interaction(retry.request_id, self.application, "query")
        fail_interaction(
            retry.request_id, "before_processing", {"response": "secret", "retry": True}
        )
        self.assertEqual(DailyUsage.objects.get(user=self.user).interaction_count, 1)
        retry.refresh_from_db()
        self.assertEqual(retry.metadata, {"retry": True})

    def test_plan_change_audit_and_blocked_check(self):
        assign_plan(self.user, "PREMIUM", reason="Manual test")
        self.assertTrue(
            PlanChangeLog.objects.filter(user=self.user, new_plan__code="PREMIUM").exists()
        )
        self.user.is_blocked = True
        self.user.save()
        with self.assertRaises(QuotaError):
            check_quota(self.user)
