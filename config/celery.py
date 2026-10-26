import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "update-share-prices": {
        "task": "dashboard.tasks.update_last_price",
        "schedule": 10.0,
    },
    "record-market-history": {
        "task": "dashboard.tasks.record_market_history",
        "schedule": 86400.0,
    },
}
