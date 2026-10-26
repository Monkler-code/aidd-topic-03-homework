from datetime import datetime, time, timedelta
from decimal import Decimal
from math import ceil

from django.utils import timezone
from plotly.graph_objs import Scatter
from plotly.offline import plot

from dashboard.models import HistoricalPrice
from dashboard.services.market_data import get_historical_candles
from dashboard.services.tbank import quotation_to_decimal

PERIOD_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
SIX_PLACES = Decimal("0.000001")
INITIAL_HISTORY_DAYS = 365
HISTORY_OVERLAP_DAYS = 2


def sync_historical_prices(share, days=None):
    if days is None:
        last_captured_at = (
            HistoricalPrice.objects.filter(share=share)
            .order_by("-captured_at")
            .values_list("captured_at", flat=True)
            .first()
        )
        if last_captured_at is None:
            days = INITIAL_HISTORY_DAYS
        else:
            fetch_from = last_captured_at - timedelta(days=HISTORY_OVERLAP_DAYS)
            days = max(1, ceil((timezone.now() - fetch_from).total_seconds() / 86400))

    candles = get_historical_candles(share, days=days)
    records = [
        HistoricalPrice(
            share=share,
            captured_at=candle.time,
            open=quotation_to_decimal(candle.open).quantize(SIX_PLACES),
            high=quotation_to_decimal(candle.high).quantize(SIX_PLACES),
            low=quotation_to_decimal(candle.low).quantize(SIX_PLACES),
            close=quotation_to_decimal(candle.close).quantize(SIX_PLACES),
            volume=candle.volume,
        )
        for candle in candles
    ]
    if records:
        HistoricalPrice.objects.bulk_create(
            records,
            update_conflicts=True,
            unique_fields=("share", "captured_at"),
            update_fields=("open", "high", "low", "close", "volume"),
        )
    return len(records)


def prices_for_period(share, period):
    if period not in PERIOD_DAYS:
        raise ValueError("Период должен быть day, week, month или year.")
    today = timezone.localdate()
    start = today - timedelta(days=PERIOD_DAYS[period] - 1)
    current_timezone = timezone.get_current_timezone()
    start_at = timezone.make_aware(datetime.combine(start, time.min), current_timezone)
    end_at = timezone.make_aware(
        datetime.combine(today + timedelta(days=1), time.min), current_timezone
    )
    return HistoricalPrice.objects.filter(
        share=share,
        captured_at__gte=start_at,
        captured_at__lt=end_at,
    ).order_by("captured_at")


def summarize_prices(prices):
    rows = list(prices)
    if not rows:
        return {
            "absolute_change": None,
            "percent_change": None,
            "first_price": None,
            "last_price": None,
        }
    first_price = rows[0].close
    last_price = rows[-1].close
    absolute_change = last_price - first_price
    return {
        "absolute_change": absolute_change,
        "percent_change": absolute_change / first_price * Decimal("100"),
        "first_price": first_price,
        "last_price": last_price,
    }


def render_price_graph(prices):
    rows = list(prices)
    return plot(
        [
            Scatter(
                x=[row.captured_at for row in rows],
                y=[float(row.close) for row in rows],
                mode="lines",
                name="Цена закрытия",
            )
        ],
        output_type="div",
        include_plotlyjs="cdn",
        show_link=False,
    )
