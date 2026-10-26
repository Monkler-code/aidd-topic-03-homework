from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    def test_registration_normalizes_email_and_logs_user_in(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "Trader@Example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("dashboard:index"))
        user = get_user_model().objects.get()
        self.assertEqual(user.email, "trader@example.com")
        self.assertTrue(user.is_authenticated)

    def test_invalid_registration_renders_errors(self):
        response = self.client.post(
            reverse("user:registration"),
            {"email": "not-an-email", "password1": "a", "password2": "b"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address")
        self.assertFalse(get_user_model().objects.exists())

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        get_user_model().objects.create_user(
            username="trader@example.com",
            email="trader@example.com",
            password="StrongPass123!",
        )
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "TRADER@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Данный e-mail уже зарегистрирован")
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_login_rejects_missing_fields_without_raising(self):
        response = self.client.post(reverse("user:auth"), {})
        self.assertEqual(response.status_code, 200)

    def test_login_accepts_legacy_mixed_case_email(self):
        user = get_user_model().objects.create_user(
            username="Legacy@Example.com",
            email="Legacy@Example.com",
            password="StrongPass123!",
        )
        response = self.client.post(
            reverse("user:auth"),
            {"email": "legacy@example.com", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.id)

    def test_logout_requires_post_and_clears_session(self):
        self.client.force_login(
            get_user_model().objects.create_user(
                username="trader@example.com",
                email="trader@example.com",
                password="StrongPass123!",
            )
        )

        get_response = self.client.get(reverse("user:logout"))
        self.assertEqual(get_response.status_code, 405)
        post_response = self.client.post(reverse("user:logout"))
        self.assertRedirects(post_response, reverse("dashboard:index"))
        self.assertNotIn("_auth_user_id", self.client.session)
