from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import Portfolio, Share, Transaction


class DashboardTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            username="trader@example.com",
            email="trader@example.com",
            password="StrongPass123!",
        )
        self.staff_user = get_user_model().objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="StrongPass123!",
            is_staff=True,
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
        self.client.force_authenticate(user=self.staff_user)
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
                "last_price": "0.01",
                "is_trend_high": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["figi"], self.apple_share.figi)
        self.assertEqual(body["name"], f"{self.apple_share.name}_test")
        self.assertEqual(body["last_price"], 100.5)

    def test_share_update_invalid(self):
        self.client.force_authenticate(user=self.staff_user)
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
        self.client.force_authenticate(user=self.staff_user)
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
        self.client.force_authenticate(user=self.staff_user)
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
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.delete(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_share_delete_invalid(self):
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete("/api/v1/shares/3/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_delete_in_use_returns_conflict(self):
        self.client.force_authenticate(user=self.staff_user)
        portfolio = Portfolio.objects.create(owner=self.user, name="Long term")
        Transaction.objects.create(
            portfolio=portfolio,
            share=self.apple_share,
            side=Transaction.Side.BUY,
            quantity=1,
            price=100,
        )

        response = self.client.delete(f"/api/v1/shares/{self.apple_share.pk}/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Share.objects.filter(pk=self.apple_share.pk).exists())

    def test_api_write_requires_authentication(self):
        response = self.client.post("/api/v1/shares/", self.second_company, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_share_update_requires_uid_only_on_create(self):
        self.client.force_authenticate(user=self.staff_user)
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

    def test_regular_user_cannot_modify_shared_catalog(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/v1/shares/{self.apple_share.pk}/",
            {"last_price": "0.01", "name": "Changed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.apple_share.refresh_from_db()
        self.assertEqual(self.apple_share.name, "Apple")
        self.assertEqual(self.apple_share.last_price, 100.50)


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

    def test_authenticated_user_cannot_create_shared_catalog_entry(self):
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
        self.assertFalse(Share.objects.filter(ticker="NEWCO").exists())

    def test_staff_user_can_create_shared_catalog_entry(self):
        user = get_user_model().objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="StrongPass123!",
            is_staff=True,
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

    def test_staff_cannot_delete_share_referenced_by_a_trade(self):
        user = get_user_model().objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="StrongPass123!",
            is_staff=True,
        )
        portfolio = Portfolio.objects.create(owner=user, name="Long term")
        Transaction.objects.create(
            portfolio=portfolio,
            share=self.share,
            side=Transaction.Side.BUY,
            quantity=1,
            price=100,
        )
        self.client.force_login(user)

        response = self.client.post(reverse("dashboard:delete", args=[self.share.pk]))

        self.assertRedirects(
            response,
            reverse("dashboard:detail", args=[self.share.pk]),
            fetch_redirect_response=False,
        )
        self.assertTrue(Share.objects.filter(pk=self.share.pk).exists())

    def test_share_detail_missing_returns_404(self):
        from dashboard.views import ShareDetailView

        with self.assertRaises(Http404):
            ShareDetailView.as_view()(RequestFactory().get("/999"), pk=999)


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

    @patch("dashboard.tasks.get_last_data_for_shares")
    def test_task_updates_price_trend_and_timestamp(self, get_last_data_for_shares):
        get_last_data_for_shares.return_value = {
            self.share.pk: (100.5, timezone.now())
        }

        from dashboard.tasks import update_last_price

        with patch("dashboard.tasks.Redis.from_url") as redis_from_url, patch(
            "dashboard.tasks.get_invest_client"
        ) as get_invest_client:
            redis_client = redis_from_url.return_value
            redis_client.lock.return_value.acquire.return_value = True
            get_invest_client.return_value.__enter__.return_value = object()
            update_last_price()
        self.share.refresh_from_db()

        self.assertEqual(self.share.last_price, 100.5)
        self.assertFalse(self.share.is_trend_high)
        self.assertGreaterEqual(self.share.updated_at, self.previous_update)

    @patch("dashboard.tasks.get_invest_client")
    @patch("dashboard.tasks.get_last_data_for_shares")
    @patch("dashboard.tasks.Redis.from_url")
    def test_task_skips_when_another_update_holds_the_lock(
        self, redis_from_url, get_last_data_for_shares, get_invest_client
    ):
        redis_from_url.return_value.lock.return_value.acquire.return_value = False

        from dashboard.tasks import update_last_price

        update_last_price()

        get_invest_client.assert_not_called()
        get_last_data_for_shares.assert_not_called()

    def test_quotation_conversion_preserves_fractional_units(self):
        from dashboard.services.tbank import quotation_to_decimal, quotation_to_float

        quotation = SimpleNamespace(units=123, nano=450_000_000)
        self.assertEqual(quotation_to_float(quotation), 123.45)
        self.assertEqual(quotation_to_decimal(quotation), Decimal("123.45"))
