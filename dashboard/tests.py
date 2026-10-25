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


# =============================================================================
# NEW MODULE TESTS
# =============================================================================


class WatchlistTests(APITestCase):
    """Tests for Watchlist and PriceAlert functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="watchlist@example.com", password="testpass123"
        )
        self.client.force_login(self.user)
        self.share = Share.objects.create(
            figi="BBG000WL001",
            isin="US0000000010",
            name="WatchTest Corp",
            ticker="WTC",
            currency="USD",
            uid="wl-uid-001",
            last_price=50.0,
        )

    def test_create_watchlist(self):
        """Test creating a watchlist via API."""
        response = self.client.post(
            "/api/v2/watchlists/",
            {"name": "My Watchlist"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "My Watchlist")
        self.assertEqual(response.data["item_count"], 0)

    def test_list_watchlists(self):
        """Test listing user's watchlists."""
        from dashboard.models import Watchlist
        Watchlist.objects.create(user=self.user, name="WL1")
        Watchlist.objects.create(user=self.user, name="WL2")
        response = self.client.get("/api/v2/watchlists/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_watchlist_detail(self):
        """Test watchlist detail view."""
        from dashboard.models import Watchlist
        wl = Watchlist.objects.create(user=self.user, name="Detail WL")
        response = self.client.get(f"/api/v2/watchlists/{wl.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail WL")

    def test_add_share_to_watchlist(self):
        """Test adding a share to a watchlist."""
        from dashboard.models import Watchlist
        wl = Watchlist.objects.create(user=self.user, name="Test WL")
        response = self.client.post(
            f"/api/v2/watchlists/{wl.id}/add_share/",
            {"share_id": self.share.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_price_alert(self):
        """Test creating a price alert."""
        from dashboard.models import Watchlist, WatchlistItem
        wl = Watchlist.objects.create(user=self.user, name="Alert WL")
        item = WatchlistItem.objects.create(watchlist=wl, share=self.share)
        response = self.client.post(
            "/api/v2/price-alerts/",
            {
                "watchlist_item_id": item.id,
                "share_id": self.share.id,
                "alert_type": "ABV",
                "target_price": 60.0,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["target_price"], 60.0)


class PortfolioTests(APITestCase):
    """Tests for Portfolio and Transaction functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="portfolio@example.com", password="testpass123"
        )
        self.client.force_login(self.user)
        self.share = Share.objects.create(
            figi="BBG000PF001",
            isin="US0000000020",
            name="Portfolio Test",
            ticker="PFT",
            currency="USD",
            uid="pf-uid-001",
            last_price=100.0,
        )

    def test_create_portfolio(self):
        """Test creating a portfolio via API."""
        response = self.client.post(
            "/api/v2/portfolios/",
            {"name": "My Portfolio"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "My Portfolio")

    def test_add_buy_transaction(self):
        """Test adding a buy transaction."""
        from dashboard.models import Portfolio
        portfolio = Portfolio.objects.create(user=self.user, name="Test Portfolio")
        response = self.client.post(
            f"/api/v2/portfolios/{portfolio.id}/add_transaction/",
            {
                "portfolio_id": portfolio.id,
                "share_id": self.share.id,
                "transaction_type": "BUY",
                "quantity": 10,
                "price": 50.0,
                "commission": 5.0,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["transaction_type"], "BUY")
        self.assertAlmostEqual(response.data["total_amount"], 505.0, places=1)

    def test_portfolio_summary(self):
        """Test portfolio summary calculation."""
        from dashboard.models import Portfolio, Transaction
        portfolio = Portfolio.objects.create(user=self.user, name="Summary Portfolio")
        Transaction.objects.create(
            portfolio=portfolio,
            share=self.share,
            transaction_type="BUY",
            quantity=10,
            price=50.0,
            commission=0,
        )
        # Update share price
        self.share.last_price = 60.0
        self.share.save()

        response = self.client.get(f"/api/v2/portfolios/{portfolio.id}/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data["total_market_value"], 0)
        self.assertGreater(response.data["total_unrealized_pnl"], 0)

    def test_portfolio_transaction_history(self):
        """Test transaction history retrieval."""
        from dashboard.models import Portfolio, Transaction
        portfolio = Portfolio.objects.create(user=self.user, name="History Portfolio")
        Transaction.objects.create(
            portfolio=portfolio,
            share=self.share,
            transaction_type="BUY",
            quantity=5,
            price=40.0,
        )
        response = self.client.get(f"/api/v2/portfolios/{portfolio.id}/transactions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class HistoricalPriceTests(TestCase):
    """Tests for HistoricalPrice model and service."""

    def setUp(self):
        self.share = Share.objects.create(
            figi="BBG000HP001",
            isin="US0000000030",
            name="History Test",
            ticker="HST",
            currency="USD",
            uid="hp-uid-001",
        )

    def test_save_historical_price(self):
        """Test saving a historical price record."""
        from datetime import date
        from dashboard.services.price_history import PriceHistoryService
        from dashboard.models import HistoricalPrice

        PriceHistoryService.save_historical_price(
            self.share, date.today(), 100.0, 105.0, 98.0, 102.0, 1000
        )
        self.assertEqual(HistoricalPrice.objects.filter(share=self.share).count(), 1)

    def test_get_price_history(self):
        """Test retrieving price history."""
        from datetime import date, timedelta
        from dashboard.services.price_history import PriceHistoryService

        # Add some historical data
        for i in range(10):
            d = date.today() - timedelta(days=i)
            PriceHistoryService.save_historical_price(
                self.share, d, 100.0 + i, 105.0 + i, 95.0 + i, 102.0 + i, 1000
            )

        data = PriceHistoryService.get_price_history(self.share)
        self.assertEqual(len(data), 10)

    def test_calculate_period_change(self):
        """Test period change calculation."""
        from datetime import date, timedelta
        from dashboard.services.price_history import PriceHistoryService

        # Add start and end prices
        start_date = date.today() - timedelta(days=30)
        end_date = date.today()
        PriceHistoryService.save_historical_price(
            self.share, start_date, 100.0, 102.0, 98.0, 100.0, 1000
        )
        PriceHistoryService.save_historical_price(
            self.share, end_date, 110.0, 112.0, 108.0, 110.0, 1000
        )

        change = PriceHistoryService.calculate_period_change(self.share, 30)
        self.assertEqual(change["start_price"], 100.0)
        self.assertEqual(change["end_price"], 110.0)
        self.assertEqual(change["absolute_change"], 10.0)
        self.assertEqual(change["percent_change"], 10.0)

    def test_build_price_chart_data(self):
        """Test chart data generation."""
        from datetime import date, timedelta
        from dashboard.services.price_history import PriceHistoryService

        for i in range(5):
            d = date.today() - timedelta(days=i)
            PriceHistoryService.save_historical_price(
                self.share, d, 100.0 + i, 105.0 + i, 95.0 + i, 102.0 + i, 1000
            )

        chart = PriceHistoryService.build_price_chart_data(self.share, 30)
        self.assertEqual(chart["count"], 5)
        self.assertEqual(len(chart["closes"]), 5)


class StrategyBacktestTests(TestCase):
    """Tests for Strategy and Backtester functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="strategy@example.com", password="testpass123"
        )
        self.share = Share.objects.create(
            figi="BBG000SB001",
            isin="US0000000040",
            name="Strategy Test",
            ticker="STT",
            currency="USD",
            uid="sb-uid-001",
            last_price=100.0,
        )
        self.strategy = __import__('dashboard.models', fromlist=['TradingStrategy']).TradingStrategy.objects.create(
            user=self.user,
            name="Test Strategy",
            description="A test strategy",
        )

    def test_create_strategy(self):
        """Test creating a trading strategy."""
        from dashboard.models import TradingStrategy
        strategy = TradingStrategy.objects.create(
            user=self.user,
            name="Another Strategy",
        )
        self.assertEqual(strategy.name, "Another Strategy")
        self.assertEqual(strategy.user, self.user)

    def test_create_strategy_rule(self):
        """Test creating a strategy rule."""
        from dashboard.models import StrategyRule
        rule = StrategyRule.objects.create(
            strategy=self.strategy,
            condition_field="close",
            condition_operator="gt",
            condition_value=100.0,
            action="BUY",
            priority=1,
        )
        self.assertEqual(rule.strategy, self.strategy)
        self.assertEqual(rule.action, "BUY")

    def test_backtest_metrics_empty(self):
        """Test backtest metrics with no trades."""
        from dashboard.services.backtester import StrategyBacktester
        metrics = StrategyBacktester.calculate_metrics([], 100000.0)
        self.assertEqual(metrics["total_trades"], 0)
        self.assertEqual(metrics["win_rate"], 0.0)
        self.assertEqual(metrics["total_return_pct"], 0.0)

    def test_backtest_metrics_with_trades(self):
        """Test backtest metrics with some trades."""
        from datetime import datetime
        from dashboard.models import StrategyTrade
        from dashboard.services.backtester import StrategyBacktester

        # Create some simulated trades
        trade1 = StrategyTrade.objects.create(
            strategy=self.strategy,
            share=self.share,
            action="BUY",
            quantity=10,
            price=100.0,
            date=datetime.now(),
        )
        trade2 = StrategyTrade.objects.create(
            strategy=self.strategy,
            share=self.share,
            action="SELL",
            quantity=10,
            price=120.0,
            date=datetime.now(),
        )

        metrics = StrategyBacktester.calculate_metrics([trade1, trade2], 100000.0)
        self.assertEqual(metrics["total_trades"], 2)
        self.assertGreater(metrics["winning_trades"], 0)
        self.assertGreater(metrics["total_return_pct"], 0)


class NewModuleAPITests(APITestCase):
    """Integration tests for new module API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="api@example.com", password="testpass123"
        )
        self.client.force_login(self.user)
        self.share = Share.objects.create(
            figi="BBG000API01",
            isin="US0000000050",
            name="API Test Corp",
            ticker="ATC",
            currency="USD",
            uid="api-uid-001",
            last_price=75.0,
        )

    def test_watchlist_list_page(self):
        """Test watchlist list page loads."""
        response = self.client.get(reverse("dashboard:watchlist-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_portfolio_list_page(self):
        """Test portfolio list page loads."""
        response = self.client.get(reverse("dashboard:portfolio-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_price_history_list_page(self):
        """Test price history list page loads."""
        response = self.client.get(reverse("dashboard:price-history-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_strategy_list_page(self):
        """Test strategy list page loads."""
        response = self.client.get(reverse("dashboard:strategy-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_watchlist_create_page(self):
        """Test watchlist create page loads."""
        response = self.client.get(reverse("dashboard:watchlist-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_portfolio_create_page(self):
        """Test portfolio create page loads."""
        response = self.client.get(reverse("dashboard:portfolio-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_strategy_create_page(self):
        """Test strategy create page loads."""
        response = self.client.get(reverse("dashboard:strategy-create"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
