"""Share model representing a stock instrument."""

from django.db import models


class Share(models.Model):
    """Акция — биржевой инструмент."""

    figi = models.CharField(max_length=255, unique=True, verbose_name="FIGI")
    isin = models.CharField(max_length=255, verbose_name="ISIN")
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True, verbose_name="UID")
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.ticker})"
