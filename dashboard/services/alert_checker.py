"""Service for checking price alerts against current market data."""

from __future__ import annotations

from dashboard.models import PriceAlert, Share
from dashboard.services.watchlists import PriceAlertService


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

        should_trigger = False
        if alert.alert_type == "ABV" and current_price >= alert.target_price:
            should_trigger = True
        elif alert.alert_type == "BLW" and current_price <= alert.target_price:
            should_trigger = True

        if should_trigger:
            if PriceAlertService.trigger_alert(alert):
                triggered_count += 1

    return triggered_count


def check_alerts_for_share(share: Share) -> int:
    """Check alerts for a specific share."""
    alerts = PriceAlert.objects.filter(
        share=share,
        is_triggered=False,
    )
    triggered_count = 0

    for alert in alerts:
        current_price = share.last_price
        if current_price is None:
            continue

        should_trigger = False
        if alert.alert_type == "ABV" and current_price >= alert.target_price:
            should_trigger = True
        elif alert.alert_type == "BLW" and current_price <= alert.target_price:
            should_trigger = True

        if should_trigger:
            if PriceAlertService.trigger_alert(alert):
                triggered_count += 1

    return triggered_count
