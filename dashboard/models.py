"""All models for the Investing application."""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


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


# =============================================================================
# MODULE 1: Watchlists & Price Alerts
# =============================================================================


class Watchlist(models.Model):
    """Список наблюдения пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="watchlists",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="Название списка")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Список наблюдения"
        verbose_name_plural = "Списки наблюдения"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.email})"

    def get_item_count(self) -> int:
        return self.items.count()


class WatchlistItem(models.Model):
    """Акция в списке наблюдения."""

    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Список наблюдения",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="watchlist_items",
        verbose_name="Акция",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Элемент списка наблюдения"
        verbose_name_plural = "Элементы списков наблюдения"
        unique_together = ["watchlist", "share"]
        ordering = ["share__name"]

    def __str__(self) -> str:
        return f"{self.watchlist.name}: {self.share.name}"


class PriceAlert(models.Model):
    """Ценовой триггер для акции."""

    class AlertType(models.TextChoices):
        ABOVE = "ABV", "Цена выше"
        BELOW = "BLW", "Цена ниже"

    watchlist_item = models.ForeignKey(
        WatchlistItem,
        on_delete=models.CASCADE,
        related_name="alerts",
        verbose_name="Элемент списка",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="price_alerts",
        verbose_name="Акция",
    )
    alert_type = models.CharField(
        max_length=3,
        choices=AlertType.choices,
        verbose_name="Тип триггера",
    )
    target_price = models.FloatField(verbose_name="Целевая цена")
    is_triggered = models.BooleanField(default=False, verbose_name="Сработал")
    triggered_at = models.DateTimeField(blank=True, null=True, verbose_name="Время срабатывания")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ценовой триггер"
        verbose_name_plural = "Ценовые триггеры"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        type_label = "выше" if self.alert_type == "ABV" else "ниже"
        return f"{self.share.name}: цена {type_label} {self.target_price}"


# =============================================================================
# MODULE 2: Portfolio & Transactions
# =============================================================================


class Portfolio(models.Model):
    """Виртуальный инвестиционный портфель."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="portfolios",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="Название портфеля")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Портфель"
        verbose_name_plural = "Портфели"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.user.email})"


class Transaction(models.Model):
    """Операция покупки/продажи в портфеле."""

    class TransactionType(models.TextChoices):
        BUY = "BUY", "Покупка"
        SELL = "SELL", "Продажа"

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Портфель",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Акция",
    )
    transaction_type = models.CharField(
        max_length=4,
        choices=TransactionType.choices,
        verbose_name="Тип операции",
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.FloatField(verbose_name="Цена за акцию")
    commission = models.FloatField(default=0, verbose_name="Комиссия")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ["-date"]
        indexes = [models.Index(fields=["portfolio", "-date"])]

    def __str__(self) -> str:
        return f"{self.transaction_type}: {self.quantity}x {self.share.name} @ {self.price}"

    @property
    def total_amount(self) -> float:
        base = self.quantity * self.price
        if self.transaction_type == "BUY":
            return base + self.commission
        return base - self.commission


# =============================================================================
# MODULE 3: Historical Price Data
# =============================================================================


class HistoricalPrice(models.Model):
    """Историческая цена акции (дневная свеча)."""

    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="historical_prices",
        verbose_name="Акция",
    )
    date = models.DateField(verbose_name="Дата")
    open_price = models.FloatField(verbose_name="Открытие")
    high = models.FloatField(verbose_name="Максимум")
    low = models.FloatField(verbose_name="Минимум")
    close = models.FloatField(verbose_name="Закрытие")
    volume = models.BigIntegerField(default=0, verbose_name="Объём")

    class Meta:
        verbose_name = "Историческая цена"
        verbose_name_plural = "Исторические цены"
        unique_together = ["share", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["share", "-date"]),
        ]

    def __str__(self) -> str:
        return f"{self.share.name} ({self.date})"


# =============================================================================
# MODULE 4: Strategy Simulator
# =============================================================================


class TradingStrategy(models.Model):
    """Торговая стратегия для бэктестинга."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="trading_strategies",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="Название стратегии")
    description = models.TextField(blank=True, verbose_name="Описание")
    is_active = models.BooleanField(default=False, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_run_at = models.DateTimeField(blank=True, null=True, verbose_name="Последний запуск")

    class Meta:
        verbose_name = "Торговая стратегия"
        verbose_name_plural = "Торговые стратегии"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.name}"


class StrategyRule(models.Model):
    """Правило торговой стратегии."""

    class ConditionField(models.TextChoices):
        CLOSE_PRICE = "close", "Цена закрытия"
        HIGH_PRICE = "high", "Максимум"
        LOW_PRICE = "low", "Минимум"
        CHANGE_PCT = "change_pct", "Изменение %"

    class ConditionOperator(models.TextChoices):
        GT = "gt", "Больше"
        LT = "lt", "Меньше"
        GTE = "gte", "Больше или равно"
        LTE = "lte", "Меньше или равно"
        CROSS_UP = "cross_up", "Пересечение вверх"
        CROSS_DOWN = "cross_down", "Пересечение вниз"

    class Action(models.TextChoices):
        BUY = "BUY", "Покупка"
        SELL = "SELL", "Продажа"

    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name="Стратегия",
    )
    condition_field = models.CharField(
        max_length=12,
        choices=ConditionField.choices,
        verbose_name="Поле условия",
    )
    condition_operator = models.CharField(
        max_length=12,
        choices=ConditionOperator.choices,
        verbose_name="Оператор",
    )
    condition_value = models.FloatField(verbose_name="Значение условия")
    action = models.CharField(
        max_length=4,
        choices=Action.choices,
        verbose_name="Действие",
    )
    priority = models.PositiveIntegerField(default=0, verbose_name="Приоритет")

    class Meta:
        verbose_name = "Правило стратегии"
        verbose_name_plural = "Правила стратегий"
        ordering = ["priority"]

    def __str__(self) -> str:
        return f"{self.strategy.name}: {self.action} if {self.condition_field} {self.condition_operator} {self.condition_value}"


class StrategyTrade(models.Model):
    """Симулированная сделка стратегии."""

    strategy = models.ForeignKey(
        TradingStrategy,
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name="Стратегия",
    )
    share = models.ForeignKey(
        Share,
        on_delete=models.CASCADE,
        related_name="strategy_trades",
        verbose_name="Акция",
    )
    action = models.CharField(max_length=4, verbose_name="Действие")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    price = models.FloatField(verbose_name="Цена")
    date = models.DateTimeField(verbose_name="Дата")
    profit_loss = models.FloatField(default=0, verbose_name="P&L")
    rule_triggered = models.CharField(
        max_length=255, blank=True, verbose_name="Сработавшее правило"
    )

    class Meta:
        verbose_name = "Симулированная сделка"
        verbose_name_plural = "Симулированные сделки"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.strategy.name}: {self.action} {self.quantity}x {self.share.name} @ {self.price}"
