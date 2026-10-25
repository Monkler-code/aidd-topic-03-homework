"""Tests for dashboard app."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import Share

User = get_user_model()


class ShareAPITests(APITestCase):
    """API tests for Share model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )
        self.second_company = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "USD",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            "last_price": 1.50,
            "is_trend_high": False,
        }

    def test_share_list(self):
        """Test that share list API returns correct data."""
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        apple_share = response.data["results"][0]
        self.assertEqual(apple_share["id"], self.apple_share.id)
        self.assertEqual(apple_share["figi"], self.apple_share.figi)
        self.assertEqual(apple_share["isin"], self.apple_share.isin)
        self.assertEqual(apple_share["name"], self.apple_share.name)
        self.assertEqual(apple_share["ticker"], self.apple_share.ticker)
        self.assertEqual(apple_share["currency"], self.apple_share.currency)

    def test_share_detail(self):
        """Test that share detail API returns correct data."""
        response = self.client.get("/api/v1/shares/")
        share_detail = response.data["results"][0]
        response = self.client.get(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Apple")

    def test_share_detail_invalid(self):
        """Test that invalid share ID returns 404."""
        response = self.client.get("/api/v1/shares/999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_create(self):
        """Test that a new share can be created via API."""
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.data
        self.assertEqual(body["figi"], self.second_company["figi"])
        self.assertEqual(body["name"], self.second_company["name"])
        self.assertEqual(body["ticker"], self.second_company["ticker"])

        response = self.client.get("/api/v1/shares/")
        self.assertEqual(len(response.data["results"]), 2)

    def test_share_create_invalid(self):
        """Test that invalid share data returns 400."""
        response = self.client.post(
            "/api/v1/shares/", {"figi": "BBG000B9XRY5"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_update(self):
        """Test that a share can be updated via API."""
        response = self.client.get("/api/v1/shares/")
        share_detail = response.data["results"][0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "id": share_detail["id"],
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "name": f"{self.apple_share.name}_test",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
                "uid": self.apple_share.uid,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.data
        self.assertEqual(body["figi"], self.apple_share.figi)
        self.assertEqual(body["name"], f"{self.apple_share.name}_test")

    def test_share_update_invalid(self):
        """Test that invalid share update returns 400."""
        response = self.client.get("/api/v1/shares/")
        share_detail = response.data["results"][0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "figi": self.apple_share.figi,
                "name": f"{self.apple_share.name}_test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_delete(self):
        """Test that a share can be deleted via API."""
        response = self.client.get("/api/v1/shares/")
        share_detail = response.data["results"][0]
        response = self.client.delete(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_share_delete_invalid(self):
        """Test that deleting invalid share returns 404."""
        response = self.client.delete("/api/v1/shares/999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_search(self):
        """Test that shares can be searched by name."""
        response = self.client.get("/api/v1/shares/?search=Apple")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_share_filter_by_ticker(self):
        """Test that shares can be filtered by ticker."""
        response = self.client.get("/api/v1/shares/?ticker=AAPL")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_share_ordering(self):
        """Test that shares can be ordered by name."""
        response = self.client.get("/api/v1/shares/?ordering=name")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["name"], "Apple")


class ShareModelTests(TestCase):
    """Tests for Share model."""

    def test_share_str(self):
        """Test Share.__str__ method."""
        share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="test-uid",
        )
        self.assertEqual(str(share), "Apple (AAPL)")

    def test_share_unique_figi(self):
        """Test that figi must be unique."""
        Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="test-uid-1",
        )
        with self.assertRaises(Exception):
            Share.objects.create(
                figi="BBG000B9XRY4",
                isin="US0378331006",
                name="Apple2",
                ticker="AAPL2",
                currency="USD",
                uid="test-uid-2",
            )

    def test_share_unique_ticker(self):
        """Test that ticker must be unique."""
        Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="USD",
            uid="test-uid-1",
        )
        with self.assertRaises(Exception):
            Share.objects.create(
                figi="BBG000B9XRY5",
                isin="US0378331006",
                name="Apple2",
                ticker="AAPL",
                currency="USD",
                uid="test-uid-2",
            )


class UserAuthTests(TestCase):
    """Tests for user authentication."""

    def setUp(self):
        self.client = Client()

    def test_login_page_loads(self):
        """Test that login page returns 200."""
        response = self.client.get("/user/login/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_registration_page_loads(self):
        """Test that registration page returns 200."""
        response = self.client.get("/user/registration/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_registration_success(self):
        """Test successful user registration."""
        response = self.client.post(
            "/user/registration/",
            {
                "email": "newuser@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_registration_duplicate_email(self):
        """Test that registering with duplicate email fails."""
        User.objects.create_user(
            email="existing@example.com", password="existingpass"
        )
        response = self.client.post(
            "/user/registration/",
            {
                "email": "existing@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("уже зарегистрирован", response.content.decode())

    def test_registration_password_mismatch(self):
        """Test that registration with mismatched passwords fails."""
        response = self.client.post(
            "/user/registration/",
            {
                "email": "mismatch@example.com",
                "password1": "Pass123!",
                "password2": "Pass456!",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("не совпадают", response.content.decode())

    def test_login_success(self):
        """Test successful user login."""
        User.objects.create_user(
            email="loginuser@example.com", password="loginpass123"
        )
        response = self.client.post(
            "/user/login/",
            {
                "email": "loginuser@example.com",
                "password": "loginpass123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(
            "/user/login/",
            {
                "email": "wrong@example.com",
                "password": "wrongpass",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Неверный логин", response.content.decode())

    def test_logout(self):
        """Test user logout."""
        user = User.objects.create_user(
            email="logoutuser@example.com", password="logoutpass123"
        )
        self.client.login(email="logoutuser@example.com", password="logoutpass123")
        response = self.client.get("/user/logout/")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)


class ShareListViewTests(TestCase):
    """Tests for share list view."""

    def setUp(self):
        self.client = Client()
        Share.objects.create(
            figi="BBG000B9XRY1",
            isin="US0000000001",
            name="Alpha",
            ticker="ALPH",
            currency="USD",
            uid="uid-alpha",
        )
        Share.objects.create(
            figi="BBG000B9XRY2",
            isin="US0000000002",
            name="Beta",
            ticker="BETA",
            currency="EUR",
            uid="uid-beta",
        )

    def test_share_list_html(self):
        """Test that share list page returns 200 and contains shares."""
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Alpha")
        self.assertContains(response, "Beta")

    def test_share_list_ordered_by_name(self):
        """Test that shares are ordered by name."""
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        alpha_pos = content.find("Alpha")
        beta_pos = content.find("Beta")
        self.assertLess(alpha_pos, beta_pos)
