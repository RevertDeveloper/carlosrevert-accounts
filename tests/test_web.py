"""Pruebas de las vistas web, la cuenta canónica y sus redirecciones seguras."""

from django.test import TestCase
from django.urls import reverse

from apps.applications.models import ClientApplication
from apps.users.models import User


class WebViewsTests(TestCase):
    """Comprueba las páginas públicas, la cuenta y los destinos de inicio de sesión."""

    def test_health_and_auth_pages(self):
        self.assertEqual(self.client.get(reverse("health")).status_code, 200)
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)

    def test_login_and_account_show_active_application_cards(self):
        ClientApplication.objects.create(
            name="Home", slug="home", base_url="https://carlosrevert.es", consumes_quota=False
        )
        ClientApplication.objects.create(
            name="Juridia", slug="juridia", base_url="https://juridia.carlosrevert.es"
        )
        ClientApplication.objects.create(
            name="Transcriptor",
            slug="transcriptor",
            base_url="https://transcriptor.carlosrevert.es",
        )
        login_response = self.client.get(reverse("login"))
        self.assertContains(login_response, "https://carlosrevert.es/favicon.svg")
        self.assertContains(login_response, "https://juridia.carlosrevert.es/apple-touch-icon.png")
        self.assertContains(login_response, "/static/favicon_io_cr/transcriptor.svg")
        self.assertNotContains(login_response, "https://transcriptor.carlosrevert.es/favicon.ico")

        user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="CorrectHorseBatteryStaple123!",
            email_verified=True,
        )
        self.client.force_login(user)
        account_response = self.client.get(reverse("account"))
        self.assertContains(account_response, "https://carlosrevert.es/favicon.svg")

    def test_account_requires_login(self):
        self.assertEqual(self.client.get(reverse("account")).status_code, 302)
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("account")).status_code, 200)

    def test_legacy_account_path_redirects_to_canonical_account(self):
        response = self.client.get("/account/")

        self.assertRedirects(response, reverse("account"), fetch_redirect_response=False)

    def test_account_updates_profile_data(self):
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("account"),
            {
                "username": "ana-nueva",
                "email": "ana@example.com",
                "first_name": "Ana",
                "last_name": "Revert",
            },
        )
        self.assertRedirects(response, reverse("account"))
        user.refresh_from_db()
        self.assertEqual(user.username, "ana-nueva")
        self.assertEqual(user.email, "ana@example.com")
        self.assertEqual(user.first_name, "Ana")
        self.assertEqual(user.last_name, "Revert")

    def test_account_update_rejects_duplicate_email(self):
        user = User.objects.create_user(
            username="ana", email="ana@example.com", password="CorrectHorseBatteryStaple123!"
        )
        User.objects.create_user(
            username="bea", email="bea@example.com", password="CorrectHorseBatteryStaple123!"
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("account"),
            {"username": "ana", "email": "bea@example.com"},
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.email, "ana@example.com")

    def test_login_only_redirects_to_carlosrevert_hosts(self):
        User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="CorrectHorseBatteryStaple123!",
            email_verified=True,
        )
        external = self.client.post(
            f"{reverse('login')}?next=https://evil.example/phishing",
            {
                "identifier": "ana",
                "password": "CorrectHorseBatteryStaple123!",
                "next": "https://evil.example/phishing",
            },
        )
        self.assertRedirects(external, reverse("account"))
        self.client.logout()
        trusted = self.client.post(
            reverse("login"),
            {
                "identifier": "ana",
                "password": "CorrectHorseBatteryStaple123!",
                "next": "https://juridia.carlosrevert.es/consulta",
            },
        )
        self.assertEqual(trusted.status_code, 302)
        self.assertEqual(trusted.url, "https://juridia.carlosrevert.es/consulta")
