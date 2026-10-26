from django.core.management.base import BaseCommand, CommandError

from dashboard.models import Share
from dashboard.services.history import sync_historical_prices


class Command(BaseCommand):
    help = "Загрузить в БД дневные свечи T-Bank Invest API для всех акций"

    def handle(self, *args, **options):
        failed = []
        for share in Share.objects.all().iterator():
            try:
                count = sync_historical_prices(share)
                self.stdout.write(f"{share.ticker}: синхронизировано свечей {count}")
            except Exception as exc:
                failed.append(share.ticker)
                self.stderr.write(f"{share.ticker}: ошибка синхронизации: {exc}")
        if failed:
            raise CommandError(
                "Не удалось синхронизировать акции: " + ", ".join(failed)
            )
