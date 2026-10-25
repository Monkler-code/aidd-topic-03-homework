"""Management command to load shares from Tinkoff Invest API."""

from django.core.management.base import BaseCommand

from config.settings import logger
from dashboard.models import Share
from tinkoff.invest import Client
from config.settings import TINKOFF_TOKEN


class Command(BaseCommand):
    """Load all available shares from Tinkoff Invest API into the database."""

    help = "Add shares to DB from Tinkoff Invest API"

    def handle(self, *args, **options):
        self.stdout.write("Loading shares from Tinkoff Invest API...")

        with Client(TINKOFF_TOKEN) as client:
            shares_response = client.instruments.shares()
            count = 0

            for share in shares_response.instruments:
                Share.objects.get_or_create(
                    figi=share.figi,
                    defaults={
                        "name": share.name,
                        "isin": share.isin,
                        "ticker": share.ticker,
                        "currency": share.currency,
                        "uid": share.uid,
                    },
                )
                count += 1

            self.stdout.write(
                self.style.SUCCESS(f"Successfully loaded {count} shares.")
            )
            logger.info("Loaded %d shares via add_shares command", count)
