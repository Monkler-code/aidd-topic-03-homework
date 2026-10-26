from rest_framework import serializers

from dashboard.models import (
    HistoricalPrice,
    Portfolio,
    PriceAlert,
    Share,
    StrategyRun,
    StrategyTrade,
    TradingStrategy,
    Transaction,
    Watchlist,
    WatchlistItem,
)
from dashboard.services.alerts import delete_alerts_without_watchlist_membership
from dashboard.services.backtesting import MAX_BACKTEST_DAYS, MAX_LOOKBACK_DAYS
from dashboard.services.portfolio import get_portfolio_summary


class WatchlistSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    shares = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    share_ids = serializers.PrimaryKeyRelatedField(
        queryset=Share.objects.all(), many=True, required=False, write_only=True
    )

    class Meta:
        model = Watchlist
        fields = ("id", "owner", "name", "shares", "share_ids", "created_at")
        read_only_fields = ("id", "created_at")

    def validate_name(self, name):
        owner = self.instance.owner if self.instance else self.context["request"].user
        duplicates = Watchlist.objects.filter(owner=owner, name=name)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Название списка уже используется.")
        return name

    def create(self, validated_data):
        shares = validated_data.pop("share_ids", [])
        owner = validated_data.pop("owner", self.context["request"].user)
        watchlist = Watchlist.objects.create(
            owner=owner, **validated_data
        )
        WatchlistItem.objects.bulk_create(
            [WatchlistItem(watchlist=watchlist, share=share) for share in shares],
            ignore_conflicts=True,
        )
        return watchlist

    def update(self, instance, validated_data):
        shares = validated_data.pop("share_ids", None)
        instance = super().update(instance, validated_data)
        if shares is not None:
            previous_share_ids = set(
                instance.items.values_list("share_id", flat=True)
            )
            new_share_ids = {share.pk for share in shares}
            instance.items.all().delete()
            WatchlistItem.objects.bulk_create(
                [WatchlistItem(watchlist=instance, share=share) for share in shares],
                ignore_conflicts=True,
            )
            delete_alerts_without_watchlist_membership(
                instance.owner_id, previous_share_ids - new_share_ids
            )
        return instance


class PriceAlertSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    share_ticker = serializers.CharField(source="share.ticker", read_only=True)

    class Meta:
        model = PriceAlert
        fields = (
            "id",
            "owner",
            "share",
            "share_ticker",
            "direction",
            "target_price",
            "status",
            "triggered_price",
            "triggered_at",
            "notification_sent_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "status",
            "triggered_price",
            "triggered_at",
            "notification_sent_at",
            "created_at",
        )

    def validate(self, attrs):
        owner = self.instance.owner if self.instance else self.context["request"].user
        share = attrs.get("share", self.instance.share if self.instance else None)
        direction = attrs.get(
            "direction", self.instance.direction if self.instance else None
        )
        target_price = attrs.get(
            "target_price", self.instance.target_price if self.instance else None
        )
        if target_price is not None and target_price <= 0:
            raise serializers.ValidationError(
                {"target_price": "Цена должна быть больше нуля."}
            )
        if share and direction and target_price is not None:
            duplicates = PriceAlert.objects.filter(
                owner=owner,
                share=share,
                direction=direction,
                target_price=target_price,
                status=PriceAlert.Status.ACTIVE,
            )
            if self.instance:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    "Такой активный алерт уже существует."
                )
        return attrs


class PortfolioSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ("id", "owner", "name", "currency", "created_at", "summary")
        read_only_fields = ("id", "created_at", "summary")

    def validate_name(self, name):
        owner = self.instance.owner if self.instance else self.context["request"].user
        duplicates = Portfolio.objects.filter(owner=owner, name=name)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Название портфеля уже используется.")
        return name

    def validate_currency(self, currency):
        if (
            self.instance
            and currency.upper() != self.instance.currency.upper()
            and self.instance.transactions.exists()
        ):
            raise serializers.ValidationError(
                "Нельзя менять валюту портфеля после добавления сделок."
            )
        return currency

    def get_summary(self, portfolio):
        summaries = self.context.get("portfolio_summaries", {})
        summary = summaries.get(portfolio.pk)
        if summary is None:
            summary = get_portfolio_summary(portfolio)
        summary["holdings"] = [
            {
                **holding,
                "share": {
                    "id": holding["share"].pk,
                    "ticker": holding["share"].ticker,
                    "name": holding["share"].name,
                    "currency": holding["share"].currency,
                },
            }
            for holding in summary["holdings"]
        ]
        return summary


class TransactionSerializer(serializers.ModelSerializer):
    portfolio = serializers.PrimaryKeyRelatedField(queryset=Portfolio.objects.all())
    share_ticker = serializers.CharField(source="share.ticker", read_only=True)

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            fields["portfolio"].queryset = Portfolio.objects.filter(
                owner=request.user
            )
        else:
            fields["portfolio"].queryset = Portfolio.objects.none()
        return fields

    class Meta:
        model = Transaction
        fields = (
            "id",
            "portfolio",
            "share",
            "share_ticker",
            "side",
            "quantity",
            "price",
            "commission",
            "realized_pnl",
            "executed_at",
        )
        read_only_fields = ("id", "realized_pnl", "executed_at")

    def validate_portfolio(self, portfolio):
        if portfolio.owner_id != self.context["request"].user.pk:
            raise serializers.ValidationError("Портфель принадлежит другому пользователю.")
        return portfolio

    def create(self, validated_data):
        from dashboard.services.portfolio import record_transaction

        try:
            return record_transaction(**validated_data)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc


class HistoricalPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalPrice
        fields = ("captured_at", "open", "high", "low", "close", "volume")


class TradingStrategySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TradingStrategy
        fields = (
            "id",
            "owner",
            "share",
            "name",
            "buy_drop_percent",
            "lookback_days",
            "sell_profit_percent",
            "commission_percent",
            "initial_capital",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        strategy = self.instance
        buy_drop = attrs.get(
            "buy_drop_percent", strategy.buy_drop_percent if strategy else None
        )
        lookback_days = attrs.get(
            "lookback_days", strategy.lookback_days if strategy else None
        )
        sell_profit = attrs.get(
            "sell_profit_percent", strategy.sell_profit_percent if strategy else None
        )
        commission = attrs.get(
            "commission_percent", strategy.commission_percent if strategy else 0
        )
        capital = attrs.get(
            "initial_capital", strategy.initial_capital if strategy else None
        )
        if buy_drop is not None and not 0 < buy_drop <= 100:
            raise serializers.ValidationError(
                {"buy_drop_percent": "Падение должно быть в диапазоне (0, 100]."}
            )
        if lookback_days is not None and lookback_days < 1:
            raise serializers.ValidationError(
                {"lookback_days": "Окно должно быть не меньше одного дня."}
            )
        if lookback_days is not None and lookback_days > MAX_LOOKBACK_DAYS:
            raise serializers.ValidationError(
                {"lookback_days": "Окно анализа не может превышать 3650 дней."}
            )
        if sell_profit is not None and sell_profit <= 0:
            raise serializers.ValidationError(
                {"sell_profit_percent": "Целевая прибыль должна быть больше нуля."}
            )
        if commission is not None and commission < 0:
            raise serializers.ValidationError(
                {"commission_percent": "Комиссия не может быть отрицательной."}
            )
        if commission is not None and commission > 100:
            raise serializers.ValidationError(
                {"commission_percent": "Комиссия не может превышать 100%."}
            )
        if capital is not None and capital <= 0:
            raise serializers.ValidationError(
                {"initial_capital": "Начальный капитал должен быть больше нуля."}
            )
        return attrs


class StrategyRunInputSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "Конечная дата должна быть не раньше начальной."}
            )
        if (attrs["end_date"] - attrs["start_date"]).days > MAX_BACKTEST_DAYS:
            raise serializers.ValidationError(
                {"end_date": "Период симуляции не может превышать 3650 дней."}
            )
        return attrs


class StrategyTradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyTrade
        fields = (
            "side",
            "executed_at",
            "quantity",
            "price",
            "commission",
            "realized_pnl",
        )


class StrategyRunSerializer(serializers.ModelSerializer):
    trades = StrategyTradeSerializer(many=True, read_only=True)
    strategy_snapshot = serializers.JSONField(read_only=True)

    class Meta:
        model = StrategyRun
        fields = (
            "id",
            "strategy",
            "strategy_snapshot",
            "start_date",
            "end_date",
            "initial_capital",
            "final_equity",
            "return_percent",
            "max_drawdown_percent",
            "winning_trades",
            "losing_trades",
            "completed_at",
            "trades",
        )


class StrategyRunListSerializer(StrategyRunSerializer):
    class Meta(StrategyRunSerializer.Meta):
        fields = tuple(
            field for field in StrategyRunSerializer.Meta.fields if field != "trades"
        )
