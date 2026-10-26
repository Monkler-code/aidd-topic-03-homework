from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import (
    HistoricalPrice,
    Portfolio,
    PriceAlert,
    Share,
    TradingStrategy,
    Transaction,
    Watchlist,
    WatchlistItem,
)
from dashboard.services.alerts import reset_alert, trigger_alerts_for_share
from dashboard.services.backtesting import run_backtest
from dashboard.services.history import summarize_prices, sync_historical_prices
from dashboard.services.portfolio import (
    calculate_positions,
    get_portfolio_summary,
    record_transaction,
)


def make_candle(share, day, close):
    captured_at = timezone.make_aware(datetime.combine(day, time(16, 0)))
    value = Decimal(str(close))
    return HistoricalPrice.objects.create(
        share=share,
        captured_at=captured_at,
        open=value,
        high=value,
        low=value,
        close=value,
        volume=100,
    )


class InvestmentServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="investor@example.com",
            email="investor@example.com",
            password="StrongPass123!",
        )
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=Decimal("22"),
        )
        self.portfolio = Portfolio.objects.create(owner=self.user, name="Long term")

    def test_average_cost_sell_pnl_and_portfolio_summary(self):
        record_transaction(
            portfolio=self.portfolio,
            share=self.share,
            side=Transaction.Side.BUY,
            quantity=Decimal("2"),
            price=Decimal("10"),
            commission=Decimal("2"),
        )
        record_transaction(
            portfolio=self.portfolio,
            share=self.share,
            side=Transaction.Side.BUY,
            quantity=Decimal("1"),
            price=Decimal("20"),
            commission=Decimal("1"),
        )
        position = calculate_positions(self.portfolio)[self.share.pk]
        self.assertEqual(position["quantity"], Decimal("3"))
        self.assertEqual(position["average_cost"], Decimal("43") / Decimal("3"))

        sale = record_transaction(
            portfolio=self.portfolio,
            share=self.share,
            side=Transaction.Side.SELL,
            quantity=Decimal("1"),
            price=Decimal("20"),
            commission=Decimal("1"),
        )
        self.assertAlmostEqual(float(sale.realized_pnl), 14 / 3, places=5)
        summary = get_portfolio_summary(self.portfolio)
        self.assertEqual(summary["holdings"][0]["quantity"], Decimal("2"))
        self.assertEqual(summary["market_value"], Decimal("44"))
        self.assertAlmostEqual(float(summary["total_pnl"]), 20.0, places=5)

    def test_cannot_sell_more_than_available_quantity(self):
        with self.assertRaisesRegex(ValueError, "Нельзя продать"):
            record_transaction(
                portfolio=self.portfolio,
                share=self.share,
                side=Transaction.Side.SELL,
                quantity=Decimal("1"),
                price=Decimal("20"),
            )
        self.assertEqual(self.portfolio.transactions.count(), 0)

    def test_alert_fires_once_until_manual_reset(self):
        alert = PriceAlert.objects.create(
            owner=self.user,
            share=self.share,
            direction=PriceAlert.Direction.ABOVE,
            target_price=Decimal("22"),
        )

        self.assertEqual(trigger_alerts_for_share(self.share, Decimal("22")), 1)
        self.assertEqual(trigger_alerts_for_share(self.share, Decimal("23")), 0)
        alert.refresh_from_db()
        self.assertEqual(alert.status, PriceAlert.Status.TRIGGERED)
        self.assertIsNotNone(alert.notification_sent_at)

        self.assertTrue(reset_alert(alert))
        self.assertEqual(trigger_alerts_for_share(self.share, Decimal("22")), 1)

    def test_history_upsert_and_period_change(self):
        candle_day = date.today() - timedelta(days=2)
        first = make_candle(self.share, candle_day, "10")
        last = make_candle(self.share, candle_day + timedelta(days=1), "12")
        summary = summarize_prices([first, last])
        self.assertEqual(summary["absolute_change"], Decimal("2"))
        self.assertEqual(summary["percent_change"], Decimal("20"))

        candle = SimpleNamespace(
            time=last.captured_at,
            open=SimpleNamespace(units=12, nano=0),
            high=SimpleNamespace(units=13, nano=0),
            low=SimpleNamespace(units=11, nano=0),
            close=SimpleNamespace(units=12, nano=500_000_000),
            volume=50,
        )
        with patch(
            "dashboard.services.history.get_historical_candles", return_value=[candle]
        ):
            self.assertEqual(sync_historical_prices(self.share), 1)
            self.assertEqual(sync_historical_prices(self.share), 1)
        self.assertEqual(self.share.historical_prices.count(), 2)
        last.refresh_from_db()
        self.assertEqual(last.close, Decimal("12.500000"))

    def test_backtest_uses_daily_prices_and_persists_trade_journal(self):
        day_one = date(2025, 1, 1)
        make_candle(self.share, day_one, "100")
        make_candle(self.share, day_one + timedelta(days=1), "90")
        make_candle(self.share, day_one + timedelta(days=2), "99")
        strategy = TradingStrategy.objects.create(
            owner=self.user,
            share=self.share,
            name="Buy dips",
            buy_drop_percent=Decimal("10"),
            lookback_days=1,
            sell_profit_percent=Decimal("10"),
            commission_percent=Decimal("0"),
            initial_capital=Decimal("1000"),
        )

        run = run_backtest(
            strategy, day_one + timedelta(days=1), day_one + timedelta(days=2)
        )

        self.assertEqual(run.final_equity, Decimal("1099.000000"))
        self.assertEqual(run.return_percent, Decimal("9.900000"))
        self.assertEqual(run.winning_trades, 1)
        self.assertEqual(run.losing_trades, 0)
        self.assertEqual(list(run.trades.values_list("side", flat=True)), ["BUY", "SELL"])

    def test_backtest_rejects_empty_price_range(self):
        strategy = TradingStrategy.objects.create(
            owner=self.user,
            share=self.share,
            name="No data",
            buy_drop_percent=Decimal("10"),
            lookback_days=1,
            sell_profit_percent=Decimal("10"),
            initial_capital=Decimal("100"),
        )
        with self.assertRaisesRegex(ValueError, "нет сохранённых"):
            run_backtest(strategy, date(2025, 1, 1), date(2025, 1, 2))


class InvestmentApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="StrongPass123!",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="StrongPass123!",
        )
        self.share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100,
        )

    def test_watchlist_is_owner_scoped(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/watchlists/",
            {"name": "Tech", "share_ids": [self.share.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["shares"], [self.share.pk])

        self.client.force_authenticate(self.other_user)
        response = self.client.get("/api/v1/watchlists/")
        self.assertEqual(response.data["count"], 0)

    def test_alert_create_trigger_and_reset_api(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/alerts/",
            {
                "share": self.share.pk,
                "direction": "above",
                "target_price": "99.5",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alert_id = response.data["id"]
        self.assertEqual(trigger_alerts_for_share(self.share, 100), 1)
        response = self.client.post(f"/api/v1/alerts/{alert_id}/reset/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "active")

    def test_alert_reset_conflict_returns_conflict_response(self):
        self.client.force_authenticate(self.user)
        payload = {
            "share": self.share.pk,
            "direction": "above",
            "target_price": "100",
        }
        first = self.client.post("/api/v1/alerts/", payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        first_id = first.data["id"]
        self.assertEqual(trigger_alerts_for_share(self.share, 100), 1)

        second = self.client.post("/api/v1/alerts/", payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        response = self.client.post(f"/api/v1/alerts/{first_id}/reset/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_portfolio_api_returns_summary_and_rejects_oversell(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/v1/portfolios/", {"name": "Demo", "currency": "USD"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        portfolio_id = response.data["id"]
        response = self.client.post(
            "/api/v1/transactions/",
            {
                "portfolio": portfolio_id,
                "share": self.share.pk,
                "side": "BUY",
                "quantity": "2",
                "price": "80",
                "commission": "1",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(f"/api/v1/portfolios/{portfolio_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["holdings"][0]["share"]["ticker"], "AAPL")

        response = self.client.post(
            "/api/v1/transactions/",
            {
                "portfolio": portfolio_id,
                "share": self.share.pk,
                "side": "SELL",
                "quantity": "3",
                "price": "90",
                "commission": "0",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_history_api_period_validation_and_results(self):
        make_candle(self.share, date.today() - timedelta(days=1), "90")
        self.client.force_authenticate(None)
        response = self.client.get(f"/api/v1/history/{self.share.pk}/?period=month")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        response = self.client.get(f"/api/v1/history/{self.share.pk}/?period=decade")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_screens_render(self):
        self.client.force_login(self.user)
        for url in ("/watchlists/", "/portfolios/", "/strategies/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)
        response = self.client.get(f"/history/{self.share.pk}/?period=month")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_strategy_run_api_returns_metrics_and_trades(self):
        self.client.force_authenticate(self.user)
        day_one = date(2025, 1, 1)
        make_candle(self.share, day_one, "100")
        make_candle(self.share, day_one + timedelta(days=1), "90")
        make_candle(self.share, day_one + timedelta(days=2), "99")
        response = self.client.post(
            "/api/v1/strategies/",
            {
                "share": self.share.pk,
                "name": "Dip buyer",
                "buy_drop_percent": "10",
                "lookback_days": 1,
                "sell_profit_percent": "10",
                "commission_percent": "0",
                "initial_capital": "1000",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        strategy_id = response.data["id"]
        response = self.client.post(
            f"/api/v1/strategies/{strategy_id}/run/",
            {
                "start_date": "2025-01-02",
                "end_date": "2025-01-03",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["return_percent"], "9.900000")
        self.assertEqual(len(response.data["trades"]), 2)

    def test_watchlist_detail_and_portfolio_detail_render(self):
        self.client.force_login(self.user)
        watchlist = Watchlist.objects.create(owner=self.user, name="Tech")
        WatchlistItem.objects.create(watchlist=watchlist, share=self.share)
        response = self.client.get(f"/watchlists/{watchlist.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "AAPL")

        portfolio = Portfolio.objects.create(owner=self.user, name="Long term")
        response = self.client.get(f"/portfolios/{portfolio.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Добавить сделку")
