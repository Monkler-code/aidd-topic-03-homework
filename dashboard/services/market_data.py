"""Service for fetching market data from Tinkoff Invest API."""

from __future__ import annotations

from datetime import datetime

from tinkoff.invest import Client

from config.settings import TINKOFF_TOKEN, logger


def get_last_data(share: object) -> tuple[float, datetime | None]:
    """
    Fetch the last price and timestamp for a share from Tinkoff API.

    Args:
        share: Share model instance (needs .figi, .id, .name attributes).

    Returns:
        tuple: (last_price: float, timestamp: datetime | None)
    """
    with Client(TINKOFF_TOKEN) as client:
        resp = client.market_data.get_last_prices(figi=[share.figi])

        if not resp.last_prices:
            logger.warning("No last prices returned for share %s (%s)", share.figi, share.id)
            return share.last_price or 0.0, None

        last_price_item = resp.last_prices[-1]
        logger.info(
            "Got last data for share %s (id=%s): price=%s",
            share.name, share.id, last_price_item.price.units,
        )
        return last_price_item.price.units, last_price_item.time
