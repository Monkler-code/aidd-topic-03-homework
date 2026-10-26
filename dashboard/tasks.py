from redis import Redis
from redis.exceptions import LockError

from config.celery import app
from config.settings import CELERY_BROKER_URL, CELERY_TASK_TIME_LIMIT, logger
from dashboard.models import Share
from dashboard.services.alerts import trigger_alerts_for_share
from dashboard.services.history import sync_historical_prices
from dashboard.services.market_data import get_last_data
from dashboard.services.tbank import get_invest_client
from django.utils import timezone


def _run_with_lock(name, callback):
    client = Redis.from_url(
        CELERY_BROKER_URL, socket_connect_timeout=5, socket_timeout=5
    )
    lock = client.lock(
        f"investing-demo:task:{name}", timeout=CELERY_TASK_TIME_LIMIT + 60
    )
    acquired = False
    try:
        acquired = lock.acquire(blocking=False)
        if not acquired:
            logger.info("Skipping %s because another task is still running", name)
            return None
        return callback()
    finally:
        if acquired:
            try:
                lock.release()
            except LockError:
                logger.warning("Lock for task %s expired before release", name)
        client.close()


def _update_last_prices():
    shares = list(Share.objects.all())
    if not shares:
        return

    with get_invest_client() as client:
        for share in shares:
            try:
                last_price, _price_time = get_last_data(share, client=client)
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
def update_last_price():
    return _run_with_lock("update_last_price", _update_last_prices)


def _record_market_history():
    for share in Share.objects.all().iterator():
        try:
            sync_historical_prices(share)
        except Exception:
            logger.exception("Could not record history for share %s", share.id)


@app.task
def record_market_history():
    return _run_with_lock("record_market_history", _record_market_history)
