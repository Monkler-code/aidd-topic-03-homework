"""API v2 serializers for new investment modules."""

from rest_framework import serializers

from dashboard.models import (
    HistoricalPrice,
    Portfolio,
    PriceAlert,
    Share,
    StrategyRule,
    StrategyTrade,
    Transaction,
    TradingStrategy,
    Watchlist,
    WatchlistItem,
)
from dashboard.services.watchlists import PriceAlertService, WatchlistService
from dashboard.services.portfolio import PortfolioCalculator


class ShareBriefSerializer(serializers.ModelSerializer):
    """Minimal share info for nested serializers."""

    class Meta:
        model = Share
        fields = ["id", "ticker", "name", "figi", "last_price", "currency"]


class WatchlistItemBriefSerializer(serializers.ModelSerializer):
    """Watchlist item with share info."""

    share = ShareBriefSerializer(read_only=True)

    class Meta:
        model = WatchlistItem
        fields = ["id", "share", "added_at"]


class WatchlistSerializer(serializers.ModelSerializer):
    """Serializer for watchlist with items."""

    items = WatchlistItemBriefSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Watchlist
        fields = ["id", "name", "items", "item_count", "created_at", "updated_at"]

    def get_item_count(self, obj) -> int:
        return obj.get_item_count()

    def create(self, validated_data):
        user = self.context["request"].user
        return WatchlistService.create_watchlist(user, validated_data["name"])


class WatchlistDetailSerializer(serializers.ModelSerializer):
    """Serializer for watchlist detail with items and prices."""

    items = serializers.SerializerMethodField()

    class Meta:
        model = Watchlist
        fields = ["id", "name", "items", "created_at", "updated_at"]

    def get_items(self, obj) -> list:
        return WatchlistService.get_watchlist_with_prices(obj)


class PriceAlertSerializer(serializers.ModelSerializer):
    """Serializer for price alerts."""

    share_ticker = serializers.CharField(source="share.ticker", read_only=True)
    share_name = serializers.CharField(source="share.name", read_only=True)
    watchlist_name = serializers.CharField(source="watchlist_item.watchlist.name", read_only=True)

    class Meta:
        model = PriceAlert
        fields = [
            "id", "share_ticker", "share_name", "watchlist_name",
            "alert_type", "target_price", "is_triggered",
            "triggered_at", "created_at",
        ]
        read_only_fields = fields


class PriceAlertCreateSerializer(serializers.Serializer):
    """Serializer for creating price alerts."""

    watchlist_item_id = serializers.IntegerField()
    share_id = serializers.IntegerField()
    alert_type = serializers.ChoiceField(choices=["ABV", "BLW"])
    target_price = serializers.FloatField(min_value=0)


class PortfolioSerializer(serializers.ModelSerializer):
    """Serializer for portfolios."""

    class Meta:
        model = Portfolio
        fields = ["id", "name", "created_at", "updated_at"]

    def create(self, validated_data):
        user = self.context["request"].user
        return PortfolioCalculator.create_portfolio(user, validated_data["name"])


class PortfolioSummarySerializer(serializers.Serializer):
    """Serializer for portfolio summary with holdings."""

    portfolio_id = serializers.IntegerField()
    name = serializers.CharField()
    holdings_count = serializers.IntegerField()
    total_market_value = serializers.FloatField()
    total_cost_basis = serializers.FloatField()
    total_unrealized_pnl = serializers.FloatField()
    total_unrealized_pnl_pct = serializers.FloatField()
    total_realized_pnl = serializers.FloatField()
    holdings = serializers.ListField(child=serializers.DictField())


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transactions."""

    share_ticker = serializers.CharField(source="share.ticker", read_only=True)
    share_name = serializers.CharField(source="share.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "share_ticker", "share_name", "transaction_type",
            "quantity", "price", "commission", "total_amount", "date",
        ]
        read_only_fields = fields


class TransactionCreateSerializer(serializers.Serializer):
    """Serializer for creating transactions."""

    portfolio_id = serializers.IntegerField()
    share_id = serializers.IntegerField()
    transaction_type = serializers.ChoiceField(choices=["BUY", "SELL"])
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.FloatField(min_value=0)
    commission = serializers.FloatField(default=0, min_value=0)


class HistoricalPriceSerializer(serializers.ModelSerializer):
    """Serializer for historical prices."""

    class Meta:
        model = HistoricalPrice
        fields = ["id", "date", "open_price", "high", "low", "close", "volume"]
        read_only_fields = fields


class PriceChangeSerializer(serializers.Serializer):
    """Serializer for price change over a period."""

    absolute_change = serializers.FloatField()
    percent_change = serializers.FloatField()
    start_price = serializers.FloatField()
    end_price = serializers.FloatField()
    high = serializers.FloatField()
    low = serializers.FloatField()
    data_points = serializers.IntegerField()


class PriceChartSerializer(serializers.Serializer):
    """Serializer for price chart data."""

    dates = serializers.ListField(child=serializers.CharField())
    closes = serializers.ListField(child=serializers.FloatField())
    opens = serializers.ListField(child=serializers.FloatField())
    highs = serializers.ListField(child=serializers.FloatField())
    lows = serializers.ListField(child=serializers.FloatField())
    volumes = serializers.ListField(child=serializers.IntegerField())
    count = serializers.IntegerField()


class TradingStrategySerializer(serializers.ModelSerializer):
    """Serializer for trading strategies."""

    rules_count = serializers.SerializerMethodField()

    class Meta:
        model = TradingStrategy
        fields = [
            "id", "name", "description", "is_active",
            "rules_count", "created_at", "updated_at", "last_run_at",
        ]

    def get_rules_count(self, obj) -> int:
        return obj.rules.count()

    def create(self, validated_data):
        user = self.context["request"].user
        return TradingStrategy.objects.create(user=user, **validated_data)


class StrategyRuleSerializer(serializers.ModelSerializer):
    """Serializer for strategy rules."""

    condition_field_display = serializers.CharField(
        source="get_condition_field_display", read_only=True
    )
    condition_operator_display = serializers.CharField(
        source="get_condition_operator_display", read_only=True
    )
    action_display = serializers.CharField(
        source="get_action_display", read_only=True
    )

    class Meta:
        model = StrategyRule
        fields = [
            "id", "condition_field", "condition_field_display",
            "condition_operator", "condition_operator_display",
            "condition_value", "action", "action_display", "priority",
        ]
        read_only_fields = fields


class StrategyRuleCreateSerializer(serializers.Serializer):
    """Serializer for creating strategy rules."""

    condition_field = serializers.ChoiceField(
        choices=["close", "high", "low", "change_pct"]
    )
    condition_operator = serializers.ChoiceField(
        choices=["gt", "lt", "gte", "lte", "cross_up", "cross_down"]
    )
    condition_value = serializers.FloatField()
    action = serializers.ChoiceField(choices=["BUY", "SELL"])
    priority = serializers.IntegerField(default=0)


class StrategyTradeSerializer(serializers.ModelSerializer):
    """Serializer for strategy trades."""

    share_ticker = serializers.CharField(source="share.ticker", read_only=True)
    share_name = serializers.CharField(source="share.name", read_only=True)

    class Meta:
        model = StrategyTrade
        fields = [
            "id", "share_ticker", "share_name", "action",
            "quantity", "price", "profit_loss", "date", "rule_triggered",
        ]
        read_only_fields = fields


class BacktestMetricsSerializer(serializers.Serializer):
    """Serializer for backtest performance metrics."""

    total_trades = serializers.IntegerField()
    buy_trades = serializers.IntegerField()
    sell_trades = serializers.IntegerField()
    winning_trades = serializers.IntegerField()
    losing_trades = serializers.IntegerField()
    win_rate = serializers.FloatField()
    total_return_pct = serializers.FloatField()
    max_drawdown_pct = serializers.FloatField()
    final_cash = serializers.FloatField()
