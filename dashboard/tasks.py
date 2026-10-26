from itertools import islice

from django.utils import timezone
from redis import Redis
from redis.exceptions import LockError

from config.celery import app
from config.settings import CELERY_TASK_TIME_LIMIT, TASK_LOCK_REDIS_URL, logger
from dashboard.models import Share
from dashboard.services.alerts import trigger_alerts_for_share
from dashboard.services.history import sync_historical_prices
from dashboard.services.market_data import (
    LAST_PRICE_BATCH_SIZE,
    get_last_data_for_shares,
)
from dashboard.services.tbank import get_invest_client


def _run_with_lock(name, callback):
    if not TASK_LOCK_REDIS_URL:
        logger.warning(
            "No Redis URL configured for task lock %s; running without a lock", name
        )
        return callback()

    client = Redis.from_url(
        TASK_LOCK_REDIS_URL,
        socket_connect_timeout=5,
        socket_timeout=5,
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
    updated_count = 0
    with get_invest_client() as client:
        shares = Share.objects.all().iterator(chunk_size=LAST_PRICE_BATCH_SIZE)
        while batch := list(islice(shares, LAST_PRICE_BATCH_SIZE)):
            try:
                prices = get_last_data_for_shares(batch, client=client)
            except Exception:
                logger.exception(
                    "Could not fetch last prices for batch of %s shares", len(batch)
                )
                continue

            for share in batch:
                quote = prices.get(share.pk)
                if quote is None:
                    logger.warning("No last price returned for share %s", share.id)
                    continue
                last_price, _price_time = quote
                try:
                    is_trend_high = (
                        last_price > share.last_price
                        if share.last_price is not None
                        and last_price != share.last_price
                        else None
                    )

                    Share.objects.filter(id=share.id).update(
                        last_price=last_price,
                        is_trend_high=is_trend_high,
                        updated_at=timezone.now(),
                    )
                    trigger_alerts_for_share(share, last_price)
                    updated_count += 1
                except Exception:
                    logger.exception("Could not update price for share %s", share.id)
    logger.info("Updated current prices for %s shares", updated_count)


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
