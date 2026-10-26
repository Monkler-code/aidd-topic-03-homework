from datetime import timedelta

from django.utils import timezone

from config.settings import logger
from dashboard.services.tbank import get_invest_client, quotation_to_decimal

LAST_PRICE_BATCH_SIZE = 100


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
    logger.debug("Got last data for share with id %s", share.id)
    return _positive_price(last_price.price), last_price.time


def get_last_data_for_shares(shares, client):
    """Fetch one batch of last prices and return quotes keyed by share id."""
    shares = list(shares)
    if not shares:
        return {}

    response = client.market_data.get_last_prices(figi=[share.figi for share in shares])
    shares_by_identifier = {}
    for share in shares:
        shares_by_identifier[share.figi] = share
        if share.uid:
            shares_by_identifier.setdefault(share.uid, share)

    result = {}
    for last_price in response.last_prices:
        try:
            price = _positive_price(last_price.price)
        except ValueError:
            continue
        for identifier in (
            getattr(last_price, "figi", None),
            getattr(last_price, "instrument_uid", None),
        ):
            share = shares_by_identifier.get(identifier)
            if share is not None:
                result[share.pk] = (price, last_price.time)
                break
    if len(shares) == 1 and not result and response.last_prices:
        last_price = response.last_prices[0]
        try:
            price = _positive_price(last_price.price)
        except ValueError:
            return result
        result[shares[0].pk] = (price, last_price.time)
    return result


def _positive_price(quotation):
    price = quotation_to_decimal(quotation)
    if price <= 0:
        raise ValueError("Market data returned a non-positive price")
    return price


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
