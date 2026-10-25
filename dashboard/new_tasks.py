"""Additional Celery tasks for new investment modules."""

from config.celery import app
from config.settings import logger
from dashboard.services.alert_checker import check_price_alerts
from dashboard.services.price_history import PriceHistoryService


@app.task
def check_all_price_alerts():
    """Check all price alerts against current market prices."""
    triggered = check_price_alerts()
    logger.info("Price alert check completed: %d alerts triggered", triggered)
    return triggered


@app.task
def collect_historical_prices():
    """Collect daily historical prices for all shares."""
    collected = PriceHistoryService.collect_daily_prices()
    logger.info("Historical price collection completed: %d prices collected", collected)
    return collected
