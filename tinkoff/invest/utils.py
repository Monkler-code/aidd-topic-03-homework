"""Mock utils for Tinkoff Invest API."""

from datetime import datetime


def now() -> datetime:
    """Return current datetime."""
    return datetime.now()
