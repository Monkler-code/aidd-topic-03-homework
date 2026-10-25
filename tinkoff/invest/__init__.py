"""Mock implementation of Tinkoff Invest API for development without API access."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Iterator


class CandleInterval(str, Enum):
    CANDLE_INTERVAL_UNSPECIFIED = "CANDLE_INTERVAL_UNSPECIFIED"
    CANDLE_INTERVAL_1_MIN = "CANDLE_INTERVAL_1_MIN"
    CANDLE_INTERVAL_5_MIN = "CANDLE_INTERVAL_5_MIN"
    CANDLE_INTERVAL_15_MIN = "CANDLE_INTERVAL_15_MIN"
    CANDLE_INTERVAL_1_HOUR = "CANDLE_INTERVAL_1_HOUR"
    CANDLE_INTERVAL_DAY = "CANDLE_INTERVAL_DAY"


class MoneyValue:
    """Mock MoneyValue from Tinkoff API."""

    def __init__(self, units: float = 0.0, nano: int = 0, currency: str = "rub"):
        self.units = units
        self.nano = nano
        self.currency = currency


class Candle:
    """Mock OHLCV candle."""

    def __init__(self, close: float = 0.0, time: datetime | None = None):
        self.close = type("Close", (), {"units": close})()
        self.time = time or datetime.now()


class ShareInstrument:
    """Mock share instrument from Tinkoff API."""

    def __init__(
        self,
        figi: str = "",
        name: str = "",
        isin: str = "",
        ticker: str = "",
        currency: str = "RUB",
        uid: str = "",
    ):
        self.figi = figi
        self.name = name
        self.isin = isin
        self.ticker = ticker
        self.currency = currency
        self.uid = uid


class SharesResponse:
    """Mock response for shares list."""

    def __init__(self, instruments: list[ShareInstrument] | None = None):
        self.instruments = instruments or []


class LastPriceItem:
    """Mock last price item."""

    def __init__(self, price: MoneyValue | None = None, time: datetime | None = None):
        self.price = price or MoneyValue()
        self.time = time or datetime.now()


class LastPricesResponse:
    """Mock response for last prices."""

    def __init__(self, last_prices: list[LastPriceItem] | None = None):
        self.last_prices = last_prices or []


class _Client:
    """Mock Tinkoff Invest Client."""

    def __init__(self, token: str = ""):
        self._token = token
        self._initialized = bool(token)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    @property
    def instruments(self) -> Any:
        if not self._initialized:
            return _MockInstruments([])
        raise ConnectionError(
            "Tinkoff Invest API token not configured. "
            "Set TINKOFF_TOKEN in config/settings.py or use mock data."
        )

    @property
    def market_data(self) -> Any:
        if not self._initialized:
            return _MockMarketData()
        raise ConnectionError(
            "Tinkoff Invest API token not configured. "
            "Set TINKOFF_TOKEN in config/settings.py or use mock data."
        )


class _MockInstruments:
    """Mock instruments namespace."""

    def __init__(self, shares: list[ShareInstrument]):
        self._shares = shares

    def shares(self) -> SharesResponse:
        if not self._shares:
            # Generate mock data
            mock_shares = [
                ShareInstrument(
                    figi=f"BBG{i:09d}",
                    name=f"Mock Company {i}",
                    isin=f"US{i:011d}",
                    ticker=f"MCK{i:03d}",
                    currency="RUB",
                    uid=f"uid-{i}",
                )
                for i in range(1, 11)
            ]
            return SharesResponse(mock_shares)
        return SharesResponse(self._shares)


class _MockMarketData:
    """Mock market_data namespace."""

    def get_last_prices(self, figi: list[str]) -> LastPricesResponse:
        prices = []
        for f in figi:
            prices.append(
                LastPriceItem(
                    price=MoneyValue(round(random.uniform(10, 1000), 2)),
                    time=datetime.now(),
                )
            )
        return LastPricesResponse(prices)

    def get_all_candles(
        self,
        figi: str,
        from_: datetime,
        interval: CandleInterval,
        to: datetime | None = None,
    ) -> Iterator[Candle]:
        """Generate mock candles for the given period."""
        if to is None:
            to = datetime.now()
        delta = to - from_
        days = max(delta.days, 1)
        for i in range(days):
            dt = from_ + timedelta(days=i)
            close = round(random.uniform(10, 1000), 2)
            yield Candle(close=close, time=dt)


def Client(token: str = "") -> _Client:
    """Factory function for Tinkoff Invest Client."""
    return _Client(token)


__all__ = [
    "Client",
    "CandleInterval",
    "Candle",
    "MoneyValue",
    "ShareInstrument",
    "SharesResponse",
    "LastPriceItem",
    "LastPricesResponse",
]
