"""Celery configuration for the Investing application."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-last-price": {
        "task": "dashboard.tasks.update_last_price",
        "schedule": 10.0,
    },
    "check-price-alerts": {
        "task": "dashboard.new_tasks.check_all_price_alerts",
        "schedule": 60.0,  # Check alerts every minute
    },
    "collect-historical-prices": {
        "task": "dashboard.new_tasks.collect_historical_prices",
        "schedule": 86400.0,  # Collect prices once per day
    },
}
