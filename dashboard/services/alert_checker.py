"""Service for checking price alerts against current market data."""

from __future__ import annotations

from dashboard.models import PriceAlert, Share
from dashboard.services.watchlists import PriceAlertService


def _should_trigger_alert(alert: PriceAlert, current_price: float) -> bool:
    """Determine whether a price alert should be triggered."""
    if alert.alert_type == "ABV" and current_price >= alert.target_price:
        return True
    if alert.alert_type == "BLW" and current_price <= alert.target_price:
        return True
    return False


def check_price_alerts() -> int:
    """
    Check all active (non-triggered) price alerts against current market prices.

    Returns the number of alerts that were triggered.
    """
    alerts = PriceAlert.objects.filter(is_triggered=False).select_related("share")
    triggered_count = 0

    for alert in alerts:
        current_price = alert.share.last_price
        if current_price is None:
            continue

        if _should_trigger_alert(alert, current_price):
            if PriceAlertService.trigger_alert(alert):
                triggered_count += 1

    return triggered_count


def check_alerts_for_share(share: Share) -> int:
    """Check alerts for a specific share."""
    alerts = PriceAlert.objects.filter(
        share=share,
        is_triggered=False,
    ).select_related("share")
    triggered_count = 0

    for alert in alerts:
        current_price = share.last_price
        if current_price is None:
            continue

        if _should_trigger_alert(alert, current_price):
            if PriceAlertService.trigger_alert(alert):
                triggered_count += 1

    return triggered_count
