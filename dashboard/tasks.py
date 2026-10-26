from config.celery import app
from config.settings import logger
from dashboard.models import Share
from dashboard.services.alerts import trigger_alerts_for_share
from dashboard.services.history import sync_historical_prices
from dashboard.services.market_data import get_last_data
from django.utils import timezone


@app.task
def update_last_price():
    shares = Share.objects.all()

    for share in shares:
        try:
            last_price, _price_time = get_last_data(share)
            is_trend_high = share.last_price is None or last_price > share.last_price

            Share.objects.filter(id=share.id).update(
                last_price=last_price,
                is_trend_high=is_trend_high,
                updated_at=timezone.now(),
            )
            trigger_alerts_for_share(share, last_price)
        except Exception:
            logger.exception("Could not update price for share %s", share.id)


@app.task
def record_market_history():
    for share in Share.objects.all().iterator():
        try:
            sync_historical_prices(share)
        except Exception:
            logger.exception("Could not record history for share %s", share.id)
