"""Service for historical price data management and analytics."""

from __future__ import annotations

from datetime import date, timedelta

from dashboard.models import HistoricalPrice, Share


class PriceHistoryService:
    """Service for historical price data operations and analytics."""

    @staticmethod
    def save_historical_price(
        share: Share,
        price_date: date,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int = 0,
    ) -> HistoricalPrice:
        """Save or update a historical price record."""
        return HistoricalPrice.objects.update_or_create(
            share=share,
            date=price_date,
            defaults={
                "open_price": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            },
        )

    @staticmethod
    def get_price_history(
        share: Share,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Get historical prices for a share within a date range."""
        qs = HistoricalPrice.objects.filter(share=share).order_by("date")

        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        return list(
            qs.values("date", "open_price", "high", "low", "close", "volume")
        )

    @staticmethod
    def get_period_data(
        share: Share,
        days: int = 30,
    ) -> list[dict]:
        """Get price data for the last N days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        return PriceHistoryService.get_price_history(share, start_date, end_date)

    @staticmethod
    def calculate_period_change(
        share: Share,
        days: int = 30,
    ) -> dict:
        """Calculate absolute and percentage change over a period."""
        data = PriceHistoryService.get_period_data(share, days)

        if len(data) < 2:
            return {
                "absolute_change": 0.0,
                "percent_change": 0.0,
                "start_price": 0.0,
                "end_price": 0.0,
                "high": 0.0,
                "low": 0.0,
                "data_points": len(data),
            }

        start_price = data[0]["close"]
        end_price = data[-1]["close"]
        absolute_change = round(end_price - start_price, 2)
        percent_change = round(((end_price - start_price) / start_price) * 100, 2) if start_price != 0 else 0.0

        all_highs = [d["high"] for d in data]
        all_lows = [d["low"] for d in data]

        return {
            "absolute_change": absolute_change,
            "percent_change": percent_change,
            "start_price": start_price,
            "end_price": end_price,
            "high": max(all_highs),
            "low": min(all_lows),
            "data_points": len(data),
        }

    @staticmethod
    def build_price_chart_data(
        share: Share,
        days: int = 180,
    ) -> dict:
        """Build chart data for a share's price history."""
        data = PriceHistoryService.get_period_data(share, days)

        dates = [d["date"].isoformat() for d in data]
        closes = [d["close"] for d in data]
        volumes = [d["volume"] for d in data]
        opens = [d["open_price"] for d in data]
        highs = [d["high"] for d in data]
        lows = [d["low"] for d in data]

        return {
            "dates": dates,
            "closes": closes,
            "opens": opens,
            "highs": highs,
            "lows": lows,
            "volumes": volumes,
            "count": len(dates),
        }

    @staticmethod
    def collect_daily_prices() -> int:
        """
        Collect daily prices for all shares from the mock Tinkoff API.
        Returns the number of prices collected.
        """
        from tinkoff.invest import Client
        from config.settings import TINKOFF_TOKEN
        from datetime import date

        shares = Share.objects.all()
        collected = 0

        with Client(TINKOFF_TOKEN) as client:
            for share in shares:
                try:
                    # Get candles for the last day
                    from tinkoff.invest.utils import now
                    from datetime import timedelta
                    from tinkoff.invest import CandleInterval

                    candles = list(client.get_all_candles(
                        figi=share.figi,
                        from_=now() - timedelta(days=1),
                        interval=CandleInterval.CANDLE_INTERVAL_DAY,
                    ))

                    if candles:
                        candle = candles[-1]
                        today = date.today()
                        PriceHistoryService.save_historical_price(
                            share=share,
                            price_date=today,
                            open_price=candle.close.units * 0.99,  # Approximate
                            high=candle.close.units * 1.02,
                            low=candle.close.units * 0.98,
                            close=candle.close.units,
                        )
                        collected += 1
                except Exception:
                    continue

        return collected
