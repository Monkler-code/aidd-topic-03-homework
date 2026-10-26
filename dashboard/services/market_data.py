from datetime import timedelta

from django.utils import timezone

from config.settings import logger
from dashboard.services.tbank import get_invest_client, quotation_to_decimal


def get_last_data(share, client=None):
    if client is None:
        with get_invest_client() as invest_client:
            return _get_last_data(share, invest_client)
    return _get_last_data(share, client)


def _get_last_data(share, client):
    response = client.market_data.get_last_prices(figi=[share.figi])
    if not response.last_prices:
        raise ValueError(f"No last price returned for share {share.figi}")
    last_price = response.last_prices[0]
    logger.info("Get last data for share with id %s", share.id)
    return quotation_to_decimal(last_price.price), last_price.time


def get_historical_candles(share, days=365):
    from t_tech.invest import CandleInterval

    with get_invest_client() as client:
        return list(
            client.get_all_candles(
                figi=share.figi,
                from_=timezone.now() - timedelta(days=days),
                interval=CandleInterval.CANDLE_INTERVAL_DAY,
            )
        )
