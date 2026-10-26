import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-share-prices": {
        "task": "dashboard.tasks.update_last_price",
        "schedule": settings.PRICE_UPDATE_INTERVAL_SECONDS,
        "options": {"expires": settings.PRICE_UPDATE_INTERVAL_SECONDS},
    },
    "record-market-history": {
        "task": "dashboard.tasks.record_market_history",
        "schedule": 86400.0,
        "options": {"expires": 86400.0},
    },
}
