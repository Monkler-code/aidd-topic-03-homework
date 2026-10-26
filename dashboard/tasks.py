"""Celery tasks for updating share market data."""

from config.celery import app
from config.settings import logger
from dashboard.models import Share
from dashboard.services.market_data import get_last_data


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_last_price(self):
    """
    Periodically update last prices and trend direction for all shares.
    Each share is updated independently — failure of one does not affect others.
    Runs every 60 seconds via Celery Beat.
    """
    shares = Share.objects.all()
    failed_figis: list[str] = []

    for share in shares:
        try:
            last_price, _datetime = get_last_data(share)

            # Determine trend: True if current price >= previous price
            if share.last_price is None:
                is_trend_high = True
            elif last_price >= share.last_price:
                is_trend_high = True
            else:
                is_trend_high = False

            Share.objects.filter(id=share.id).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
            )
        except Exception as exc:
            logger.error("Failed to update share %s: %s", share.figi, exc)
            failed_figis.append(share.figi)

    if failed_figis:
        logger.warning(
            "update_last_price: %d/%d shares failed: %s",
            len(failed_figis),
            shares.count(),
            ", ".join(failed_figis),
        )
