from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.plans.models import UserPlan
from apps.users.models import User


class AuthenticationApiTests(TestCase):
    def test_registration_creates_pending_demo_plan_user_without_session(self):
        response = self.client.post(
            reverse("api-register"),
            {
                "username": "ana",
                "email": "ana@example.com",
                "password": "CorrectHorseBatteryStaple123!",
                "accepted_terms": True,
            },
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="ana@example.com")
        self.assertTrue(user.check_password("CorrectHorseBatteryStaple123!"))
        assignment = UserPlan.objects.get(user=user)
        self.assertEqual(assignment.plan.code, "FREE")
        self.assertEqual(assignment.plan.name, "Acceso de demostración")
        self.assertFalse(user.email_verified)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)

    def test_duplicate_email_and_weak_password_are_rejected(self):
        User.objects.create_user(
            username="taken", email="taken@example.com", password="CorrectHorseBatteryStaple123!"
        )
        duplicate = self.client.post(
            reverse("api-register"),
            {
                "username": "other",
                "email": "taken@example.com",
                "password": "CorrectHorseBatteryStaple123!",
                "accepted_terms": True,
            },
        )
        weak = self.client.post(
            reverse("api-register"),
            {
                "username": "weak",
                "email": "weak@example.com",
                "password": "12345678",
                "accepted_terms": True,
            },
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(weak.status_code, 400)

    def test_six_character_password_and_username_like_password_are_allowed(self):
        response = self.client.post(
            reverse("api-register"),
            {
                "username": "zxqvbn",
                "email": "short@example.com",
                "password": "zxqvbn",
                "accepted_terms": True,
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_login_logout_and_blocked_user(self):
        user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="CorrectHorseBatteryStaple123!",
            email_verified=True,
        )
        login = self.client.post(
            reverse("api-login"),
            {"identifier": "ana@example.com", "password": "CorrectHorseBatteryStaple123!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.post(reverse("api-logout")).status_code, 204)
        user.is_blocked = True
        user.save()
        blocked = self.client.post(
            reverse("api-login"), {"identifier": "ana", "password": "CorrectHorseBatteryStaple123!"}
        )
        self.assertEqual(blocked.status_code, 400)
