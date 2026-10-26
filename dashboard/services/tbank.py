"""Small compatibility boundary for the T-Bank Invest SDK."""

from decimal import Decimal

from config.settings import TINKOFF_TOKEN


def get_invest_client(token=None):
    """Create the T-Bank client, importing the optional SDK only on demand."""
    try:
        from t_tech.invest import Client
    except ImportError as exc:
        raise RuntimeError(
            "T-Bank Invest SDK is missing; install dependencies from requirements.txt"
        ) from exc

    access_token = token or TINKOFF_TOKEN
    if not access_token:
        raise RuntimeError("Set TINKOFF_TOKEN to use market-data features")
    return Client(access_token)


def quotation_to_float(quotation):
    """Convert the SDK's units/nano quotation into a float for compatibility."""
    return float(quotation_to_decimal(quotation))


def quotation_to_decimal(quotation):
    return Decimal(quotation.units) + Decimal(quotation.nano) / Decimal(1_000_000_000)
