"""API v2 views for new investment modules."""

from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
from dashboard.services.alert_checker import check_price_alerts
from dashboard.services.backtester import StrategyBacktester
from dashboard.services.portfolio import PortfolioCalculator
from dashboard.services.price_history import PriceHistoryService
from dashboard.services.watchlists import PriceAlertService, WatchlistService

from .serializers import (
    BacktestMetricsSerializer,
    HistoricalPriceSerializer,
    PortfolioSerializer,
    PortfolioSummarySerializer,
    PriceAlertCreateSerializer,
    PriceAlertSerializer,
    PriceChangeSerializer,
    PriceChartSerializer,
    StrategyRuleCreateSerializer,
    StrategyRuleSerializer,
    StrategyTradeSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
    TradingStrategySerializer,
    WatchlistDetailSerializer,
    WatchlistSerializer,
)


class WatchlistViewSet(viewsets.ModelViewSet):
    """API for managing watchlists."""

    serializer_class = WatchlistSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user).prefetch_related("items__share")

    def get_serializer_class(self):
        if self.action == "detail":
            return WatchlistDetailSerializer
        return WatchlistSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def add_share(self, request, pk=None):
        """Add a share to a watchlist."""
        watchlist = self.get_object()
        share_id = request.data.get("share_id")
        if not share_id:
            return Response({"error": "share_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = Share.objects.get(id=share_id)
        except Share.DoesNotExist:
            return Response({"error": "Share not found"}, status=status.HTTP_404_NOT_FOUND)

        item = WatchlistService.add_share_to_watchlist(watchlist, share)
        return Response({"message": "Share added", "item_id": item.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"])
    def remove_share(self, request, pk=None):
        """Remove a share from a watchlist."""
        watchlist = self.get_object()
        share_id = request.data.get("share_id")
        if not share_id:
            return Response({"error": "share_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        success = WatchlistService.remove_share_from_watchlist(watchlist, share_id)
        if success:
            return Response({"message": "Share removed"})
        return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"])
    def items(self, request, pk=None):
        """Get watchlist items with current prices."""
        watchlist = self.get_object()
        items = WatchlistService.get_watchlist_with_prices(watchlist)
        return Response(items)


class PriceAlertViewSet(viewsets.ModelViewSet):
    """API for managing price alerts."""

    serializer_class = PriceAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PriceAlert.objects.filter(
            watchlist_item__watchlist__user=self.request.user
        ).select_related("share", "watchlist_item__watchlist")

    def create(self, request, *args, **kwargs):
        """Create a new price alert."""
        serializer = PriceAlertCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            watchlist_item = WatchlistItem.objects.get(
                id=serializer.validated_data["watchlist_item_id"],
                watchlist__user=request.user,
            )
            share = Share.objects.get(id=serializer.validated_data["share_id"])
        except (WatchlistItem.DoesNotExist, Share.DoesNotExist):
            return Response({"error": "Watchlist item or share not found"}, status=status.HTTP_404_NOT_FOUND)

        alert = PriceAlertService.create_alert(
            watchlist_item=watchlist_item,
            share=share,
            alert_type=serializer.validated_data["alert_type"],
            target_price=serializer.validated_data["target_price"],
        )

        return Response(PriceAlertSerializer(alert).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def trigger(self, request, pk=None):
        """Manually trigger an alert (for testing)."""
        alert = self.get_object()
        triggered = PriceAlertService.trigger_alert(alert)
        if triggered:
            return Response({"message": "Alert triggered"})
        return Response({"message": "Alert already triggered"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reset(self, request, pk=None):
        """Reset a triggered alert."""
        alert = self.get_object()
        PriceAlertService.reset_alert(alert)
        return Response({"message": "Alert reset"})

    @action(detail=False, methods=["get"])
    def check_all(self, request):
        """Check all alerts against current prices."""
        triggered = check_price_alerts()
        return Response({"triggered_count": triggered})


class PortfolioViewSet(viewsets.ModelViewSet):
    """API for managing portfolios."""

    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Get portfolio summary with holdings and P&L."""
        portfolio = self.get_object()
        summary = PortfolioCalculator.get_portfolio_summary(portfolio)
        return Response(PortfolioSummarySerializer(summary).data)

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        """Get transaction history for a portfolio."""
        portfolio = self.get_object()
        history = PortfolioCalculator.get_transaction_history(portfolio)
        return Response(history)

    @action(detail=True, methods=["post"])
    def add_transaction(self, request, pk=None):
        """Add a transaction to a portfolio."""
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            portfolio = Portfolio.objects.get(id=serializer.validated_data["portfolio_id"], user=request.user)
            share = Share.objects.get(id=serializer.validated_data["share_id"])
        except (Portfolio.DoesNotExist, Share.DoesNotExist):
            return Response({"error": "Portfolio or share not found"}, status=status.HTTP_404_NOT_FOUND)

        tx = PortfolioCalculator.add_transaction(
            portfolio=portfolio,
            share=share,
            transaction_type=serializer.validated_data["transaction_type"],
            quantity=serializer.validated_data["quantity"],
            price=serializer.validated_data["price"],
            commission=serializer.validated_data.get("commission", 0),
        )

        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class HistoricalPriceViewSet(viewsets.ReadOnlyModelViewSet):
    """API for historical price data."""

    serializer_class = HistoricalPriceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HistoricalPrice.objects.all().order_by("-date")

    def get_queryset(self):
        queryset = HistoricalPrice.objects.all()
        share_id = self.request.query_params.get("share_id")
        if share_id:
            queryset = queryset.filter(share_id=share_id)
        return queryset.order_by("-date")

    @action(detail=False, methods=["get"], url_path="change")
    def change(self, request):
        """Get price change over a period."""
        share_id = request.query_params.get("share_id")
        days = int(request.query_params.get("days", 30))

        if not share_id:
            return Response({"error": "share_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = Share.objects.get(id=share_id)
        except Share.DoesNotExist:
            return Response({"error": "Share not found"}, status=status.HTTP_404_NOT_FOUND)

        change_data = PriceHistoryService.calculate_period_change(share, days)
        return Response(PriceChangeSerializer(change_data).data)

    @action(detail=False, methods=["get"], url_path="chart")
    def chart(self, request):
        """Get chart data for a share."""
        share_id = request.query_params.get("share_id")
        days = int(request.query_params.get("days", 180))

        if not share_id:
            return Response({"error": "share_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = Share.objects.get(id=share_id)
        except Share.DoesNotExist:
            return Response({"error": "Share not found"}, status=status.HTTP_404_NOT_FOUND)

        chart_data = PriceHistoryService.build_price_chart_data(share, days)
        return Response(PriceChartSerializer(chart_data).data)


class TradingStrategyViewSet(viewsets.ModelViewSet):
    """API for trading strategies."""

    serializer_class = TradingStrategySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TradingStrategy.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get"], url_path="rules")
    def get_rules(self, request, pk=None):
        """Get rules for a strategy."""
        strategy = self.get_object()
        rules = strategy.rules.all()
        return Response(StrategyRuleSerializer(rules, many=True).data)

    @action(detail=True, methods=["post"], url_path="rules")
    def add_rule(self, request, pk=None):
        """Add a rule to a strategy."""
        serializer = StrategyRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        strategy = self.get_object()
        rule = StrategyRule.objects.create(
            strategy=strategy,
            condition_field=serializer.validated_data["condition_field"],
            condition_operator=serializer.validated_data["condition_operator"],
            condition_value=serializer.validated_data["condition_value"],
            action=serializer.validated_data["action"],
            priority=serializer.validated_data.get("priority", 0),
        )

        return Response(StrategyRuleSerializer(rule).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="backtest")
    def backtest(self, request, pk=None):
        """Run a backtest for a strategy."""
        strategy = self.get_object()
        share_id = request.data.get("share_id")
        days = int(request.data.get("days", 365))

        if not share_id:
            return Response({"error": "share_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            share = Share.objects.get(id=share_id)
        except Share.DoesNotExist:
            return Response({"error": "Share not found"}, status=status.HTTP_404_NOT_FOUND)

        backtester = StrategyBacktester(strategy)
        trades = backtester.run_backtest(share, days)
        metrics = StrategyBacktester.calculate_metrics(trades, backtester.virtual_cash)

        return Response({
            "metrics": BacktestMetricsSerializer(metrics).data,
            "trades": StrategyTradeSerializer(trades, many=True).data,
        })

    @action(detail=True, methods=["get"], url_path="trades")
    def get_trades(self, request, pk=None):
        """Get trades for a strategy."""
        strategy = self.get_object()
        trades = strategy.trades.all()
        return Response(StrategyTradeSerializer(trades, many=True).data)
