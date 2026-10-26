from datetime import timedelta

from django.utils import timezone

from dashboard.models import HistoricalPrice
from dashboard.services.history import render_price_graph, sync_historical_prices


def get_graph(share):
    prices = HistoricalPrice.objects.filter(
        share=share, captured_at__gte=timezone.now() - timedelta(days=180)
    ).order_by("captured_at")
    if not prices.exists():
        sync_historical_prices(share, days=180)
        prices = HistoricalPrice.objects.filter(
            share=share, captured_at__gte=timezone.now() - timedelta(days=180)
        ).order_by("captured_at")
    return render_price_graph(prices)
