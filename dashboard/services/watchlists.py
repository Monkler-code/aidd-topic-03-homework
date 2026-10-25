"""Service for managing watchlists and price alerts."""

from __future__ import annotations

from django.db import transaction

from dashboard.models import (
    PriceAlert,
    Share,
    Watchlist,
    WatchlistItem,
)


class WatchlistService:
    """Service for watchlist management operations."""

    @staticmethod
    def create_watchlist(user, name: str) -> Watchlist:
        """Create a new watchlist for the user."""
        return Watchlist.objects.create(user=user, name=name)

    @staticmethod
    def add_share_to_watchlist(watchlist: Watchlist, share: Share) -> WatchlistItem:
        """Add a share to a watchlist, avoiding duplicates."""
        item, created = WatchlistItem.objects.get_or_create(
            watchlist=watchlist,
            share=share,
        )
        return item

    @staticmethod
    def remove_share_from_watchlist(watchlist: Watchlist, share: Share) -> bool:
        """Remove a share from a watchlist."""
        return WatchlistItem.objects.filter(watchlist=watchlist, share=share).delete()[0] > 0

    @staticmethod
    def get_user_watchlists(user) -> list[Watchlist]:
        """Get all watchlists for a user."""
        return list(Watchlist.objects.filter(user=user).prefetch_related("items__share"))

    @staticmethod
    def get_watchlist_with_prices(watchlist: Watchlist) -> dict:
        """Get watchlist items with current prices."""
        items = watchlist.items.select_related("share").all()
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "share_id": item.share.id,
                "ticker": item.share.ticker,
                "name": item.share.name,
                "figi": item.share.figi,
                "last_price": item.share.last_price,
                "currency": item.share.currency,
                "is_trend_high": item.share.is_trend_high,
            })
        return result


class PriceAlertService:
    """Service for price alert management and checking."""

    @staticmethod
    def create_alert(
        watchlist_item: WatchlistItem,
        share: Share,
        alert_type: str,
        target_price: float,
    ) -> PriceAlert:
        """Create a new price alert."""
        return PriceAlert.objects.create(
            watchlist_item=watchlist_item,
            share=share,
            alert_type=alert_type,
            target_price=target_price,
        )

    @staticmethod
    def get_active_alerts_for_share(share: Share) -> list[PriceAlert]:
        """Get all non-triggered alerts for a share."""
        return list(
            PriceAlert.objects.filter(
                share=share,
                is_triggered=False,
            ).select_related("watchlist_item__watchlist")
        )

    @staticmethod
    def get_user_alerts(user) -> list[dict]:
        """Get all alerts for a user's watchlists."""
        alerts = (
            PriceAlert.objects.filter(
                watchlist_item__watchlist__user=user,
            )
            .select_related("share", "watchlist_item__watchlist")
            .order_by("-created_at")
        )
        result = []
        for alert in alerts:
            result.append({
                "id": alert.id,
                "alert_type": alert.get_alert_type_display(),
                "target_price": alert.target_price,
                "is_triggered": alert.is_triggered,
                "share_ticker": alert.share.ticker,
                "share_name": alert.share.name,
                "share_last_price": alert.share.last_price,
                "watchlist_name": alert.watchlist_item.watchlist.name,
                "created_at": alert.created_at,
                "triggered_at": alert.triggered_at,
            })
        return result

    @staticmethod
    def trigger_alert(alert: PriceAlert) -> bool:
        """Mark an alert as triggered (prevents duplicate notifications)."""
        if alert.is_triggered:
            return False
        with transaction.atomic():
            alert.refresh_from_db()
            if alert.is_triggered:
                return False
            alert.is_triggered = True
            alert.triggered_at = alert.triggered_at or __import__("datetime").datetime.now()
            alert.save(update_fields=["is_triggered", "triggered_at"])
        return True

    @staticmethod
    def reset_alert(alert: PriceAlert) -> bool:
        """Reset a triggered alert so it can trigger again."""
        alert.is_triggered = False
        alert.triggered_at = None
        alert.save(update_fields=["is_triggered", "triggered_at"])
        return True

    @staticmethod
    def delete_alert(alert: PriceAlert) -> bool:
        """Delete an alert."""
        count, _ = alert.delete()
        return count > 0
