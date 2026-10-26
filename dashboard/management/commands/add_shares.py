from django.core.management.base import BaseCommand

from dashboard.models import Share
from dashboard.services.tbank import get_invest_client


class Command(BaseCommand):
    help = "Add shares to DB"

    def handle(self, *args, **options):
        with get_invest_client() as client:
            shares = client.instruments.shares()
            for share in shares.instruments:
                Share.objects.get_or_create(
                    figi=share.figi,
                    name=share.name,
                    isin=share.isin,
                    ticker=share.ticker,
                    currency=share.currency,
                    uid=share.uid,
                )


