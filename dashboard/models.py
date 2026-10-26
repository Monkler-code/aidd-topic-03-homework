from django.db import models
from django.conf import settings
from django.db.models import Q


class Share(models.Model):
    """Акция"""

    figi = models.CharField(max_length=255, unique=True)
    isin = models.CharField(max_length=255)
    name = models.CharField(max_length=255, verbose_name="Наименование компании")
    ticker = models.CharField(max_length=10, unique=True, verbose_name="Тикер")
    currency = models.CharField(max_length=20, verbose_name="Валюта")
    uid = models.CharField(max_length=255, unique=True)
    last_price = models.FloatField(blank=True, null=True, verbose_name="Текущая цена")
    is_trend_high = models.BooleanField(
        blank=True, null=True, verbose_name="Растет цена"
    )
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции"


class Watchlist(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="watchlists"
    )
    name = models.CharField(max_length=100)
    shares = models.ManyToManyField(Share, through="WatchlistItem", related_name="watchlists")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.UniqueConstraint(fields=("owner", "name"), name="uniq_watchlist_owner_name")
        ]

    def __str__(self):
        return self.name


class WatchlistItem(models.Model):
    watchlist = models.ForeignKey(
        Watchlist, on_delete=models.CASCADE, related_name="items"
    )
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="watchlist_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("watchlist", "share"), name="uniq_watchlist_share"
            )
        ]


class PriceAlert(models.Model):
    class Direction(models.TextChoices):
        ABOVE = "above", "Выше или равно"
        BELOW = "below", "Ниже или равно"

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        TRIGGERED = "triggered", "Сработал"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="price_alerts"
    )
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="alerts")
    direction = models.CharField(max_length=8, choices=Direction.choices)
    target_price = models.DecimalField(max_digits=20, decimal_places=6)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    triggered_price = models.DecimalField(
        max_digits=20, decimal_places=6, null=True, blank=True
    )
    triggered_at = models.DateTimeField(null=True, blank=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("status", "created_at")
        constraints = [
            models.CheckConstraint(
                check=Q(target_price__gt=0), name="alert_target_price_positive"
            ),
            models.UniqueConstraint(
                fields=("owner", "share", "direction", "target_price"),
                condition=Q(status="active"),
                name="uniq_active_price_alert",
            ),
        ]


class Portfolio(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios"
    )
    name = models.CharField(max_length=100)
    currency = models.CharField(max_length=10, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.UniqueConstraint(fields=("owner", "name"), name="uniq_portfolio_owner_name")
        ]

    def __str__(self):
        return self.name


class Transaction(models.Model):
    class Side(models.TextChoices):
        BUY = "BUY", "Покупка"
        SELL = "SELL", "Продажа"

    portfolio = models.ForeignKey(
        Portfolio, on_delete=models.CASCADE, related_name="transactions"
    )
    share = models.ForeignKey(Share, on_delete=models.PROTECT, related_name="transactions")
    side = models.CharField(max_length=4, choices=Side.choices)
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    price = models.DecimalField(max_digits=20, decimal_places=6)
    commission = models.DecimalField(
        max_digits=20, decimal_places=6, default=0
    )
    realized_pnl = models.DecimalField(
        max_digits=20, decimal_places=6, default=0
    )
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("executed_at", "id")
        constraints = [
            models.CheckConstraint(check=Q(quantity__gt=0), name="transaction_quantity_positive"),
            models.CheckConstraint(check=Q(price__gt=0), name="transaction_price_positive"),
            models.CheckConstraint(check=Q(commission__gte=0), name="transaction_commission_nonnegative"),
        ]


class HistoricalPrice(models.Model):
    share = models.ForeignKey(
        Share, on_delete=models.CASCADE, related_name="historical_prices"
    )
    captured_at = models.DateTimeField()
    open = models.DecimalField(max_digits=20, decimal_places=6)
    high = models.DecimalField(max_digits=20, decimal_places=6)
    low = models.DecimalField(max_digits=20, decimal_places=6)
    close = models.DecimalField(max_digits=20, decimal_places=6)
    volume = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("captured_at", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("share", "captured_at"), name="uniq_share_candle_time"
            ),
            models.CheckConstraint(check=Q(close__gt=0), name="historical_close_positive"),
        ]


class TradingStrategy(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trading_strategies"
    )
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name="strategies")
    name = models.CharField(max_length=100)
    buy_drop_percent = models.DecimalField(max_digits=8, decimal_places=4)
    lookback_days = models.PositiveSmallIntegerField(default=7)
    sell_profit_percent = models.DecimalField(max_digits=8, decimal_places=4)
    commission_percent = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    initial_capital = models.DecimalField(max_digits=20, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [
            models.CheckConstraint(
                check=Q(buy_drop_percent__gt=0) & Q(buy_drop_percent__lte=100),
                name="strategy_drop_percent_range",
            ),
            models.CheckConstraint(
                check=Q(sell_profit_percent__gt=0), name="strategy_profit_positive"
            ),
            models.CheckConstraint(
                check=Q(lookback_days__gt=0), name="strategy_lookback_days_positive"
            ),
            models.CheckConstraint(
                check=Q(commission_percent__gte=0), name="strategy_commission_nonnegative"
            ),
            models.CheckConstraint(
                check=Q(initial_capital__gt=0), name="strategy_capital_positive"
            ),
        ]


class StrategyRun(models.Model):
    strategy = models.ForeignKey(
        TradingStrategy, on_delete=models.CASCADE, related_name="runs"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=20, decimal_places=6)
    final_equity = models.DecimalField(max_digits=20, decimal_places=6)
    return_percent = models.DecimalField(max_digits=12, decimal_places=6)
    max_drawdown_percent = models.DecimalField(max_digits=12, decimal_places=6)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-completed_at", "-id")


class StrategyTrade(models.Model):
    class Side(models.TextChoices):
        BUY = "BUY", "Покупка"
        SELL = "SELL", "Продажа"

    run = models.ForeignKey(StrategyRun, on_delete=models.CASCADE, related_name="trades")
    side = models.CharField(max_length=4, choices=Side.choices)
    executed_at = models.DateTimeField()
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    price = models.DecimalField(max_digits=20, decimal_places=6)
    commission = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    realized_pnl = models.DecimalField(max_digits=20, decimal_places=6, default=0)

    class Meta:
        ordering = ("executed_at", "id")
