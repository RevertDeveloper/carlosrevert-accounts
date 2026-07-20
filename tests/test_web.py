from django.test import TestCase
from django.urls import reverse

from apps.users.models import User


class WebViewsTests(TestCase):
    def test_health_and_auth_pages(self):
        self.assertEqual(self.client.get(reverse("health")).status_code, 200)
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)

    def test_account_requires_login(self):
        self.assertEqual(self.client.get(reverse("account")).status_code, 302)
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("account")).status_code, 200)
