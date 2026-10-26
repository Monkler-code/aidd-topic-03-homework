from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from types import SimpleNamespace
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from dashboard.models import Share


class DashboardTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="trader@example.com",
            email="trader@example.com",
            password="StrongPass123!",
        )
        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )

        self.second_company = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "usd",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            "last_price": 1.50,
            "is_trend_high": False,
        }

    def test_share_list_html(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_list(self):
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        apple_share = response.json().get("results")[0]
        self.assertEqual(apple_share["id"], self.apple_share.id)
        self.assertEqual(apple_share["figi"], self.apple_share.figi)
        self.assertEqual(apple_share["isin"], self.apple_share.isin)
        self.assertEqual(apple_share["name"], self.apple_share.name)
        self.assertEqual(apple_share["ticker"], self.apple_share.ticker)
        self.assertEqual(apple_share["currency"], self.apple_share.currency)

    def test_share_detail(self):
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.get(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_detail_invalid(self):
        response = self.client.get("/api/v1/shares/2/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_update(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "id": share_detail["id"],
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "name": f"{self.apple_share.name}_test",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["figi"], self.apple_share.figi)
        self.assertEqual(body["name"], f"{self.apple_share.name}_test")

    def test_share_update_invalid(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "figi": self.apple_share.figi,
                "name": f"{self.apple_share.name}_test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_create(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["figi"], self.second_company["figi"])
        self.assertEqual(body["name"], self.second_company["name"])
        self.assertEqual(body["ticker"], self.second_company["ticker"])

        response = self.client.get("/api/v1/shares/")
        self.assertEqual(len(response.data["results"]), 2)

    def test_share_create_invalid(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/v1/shares/",
            {
                "figi": "BBG000B9XRY5",
                "isin": "US0378331004",
                "name": "New Company",
                "ticker": "NEWCO",
                "currency": "usd",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("uid", response.data)

    def test_share_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.delete(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_share_delete_invalid(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete("/api/v1/shares/3/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_api_write_requires_authentication(self):
        response = self.client.post("/api/v1/shares/", self.second_company, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_share_update_requires_uid_only_on_create(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            f"/api/v1/shares/{self.apple_share.id}/",
            {
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "name": "Updated Apple",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uid"], self.apple_share.uid)


class ShareWebTests(TestCase):
    def setUp(self):
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
        )

    def test_share_detail_renders_graph(self):
        with patch("dashboard.views.get_graph", return_value="<div>graph</div>"):
            response = self.client.get(reverse("dashboard:detail", args=[self.share.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")
        self.assertContains(response, "graph")

    def test_share_create_redirects_anonymous_user(self):
        response = self.client.get(reverse("dashboard:create"))
        self.assertRedirects(response, reverse("dashboard:index"))

    def test_authenticated_user_can_create_share(self):
        user = get_user_model().objects.create_user(
            username="trader@example.com",
            email="trader@example.com",
            password="StrongPass123!",
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse("dashboard:create"),
            {
                "figi": "BBG000B9XRY5",
                "isin": "US0378331004",
                "name": "New Company",
                "ticker": "NEWCO",
                "currency": "usd",
                "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            },
        )

        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(Share.objects.filter(ticker="NEWCO").exists())


class PriceUpdateTests(TestCase):
    def setUp(self):
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.5,
        )
        self.previous_update = self.share.updated_at

    @patch("dashboard.tasks.get_last_data")
    def test_task_updates_price_trend_and_timestamp(self, get_last_data):
        get_last_data.return_value = (100.5, timezone.now())

        from dashboard.tasks import update_last_price

        update_last_price()
        self.share.refresh_from_db()

        self.assertEqual(self.share.last_price, 100.5)
        self.assertFalse(self.share.is_trend_high)
        self.assertGreaterEqual(self.share.updated_at, self.previous_update)

    def test_quotation_conversion_preserves_fractional_units(self):
        from dashboard.services.tbank import quotation_to_float

        quotation = SimpleNamespace(units=123, nano=450_000_000)
        self.assertEqual(quotation_to_float(quotation), 123.45)
