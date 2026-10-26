from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.api.v1.investment_serializers import (
    HistoricalPriceSerializer,
    PortfolioSerializer,
    PriceAlertSerializer,
    StrategyRunInputSerializer,
    StrategyRunSerializer,
    TradingStrategySerializer,
    TransactionSerializer,
    WatchlistSerializer,
)
from dashboard.models import (
    Portfolio,
    PriceAlert,
    Share,
    StrategyRun,
    TradingStrategy,
    Transaction,
    Watchlist,
)
from dashboard.services.alerts import reset_alert
from dashboard.services.backtesting import run_backtest
from dashboard.services.history import PERIOD_DAYS, prices_for_period, summarize_prices


class OwnerModelViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)


class WatchlistViewSet(OwnerModelViewSet):
    serializer_class = WatchlistSerializer

    def get_queryset(self):
        return Watchlist.objects.filter(owner=self.request.user).prefetch_related("shares")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PriceAlertViewSet(OwnerModelViewSet):
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        return PriceAlert.objects.filter(owner=self.request.user).select_related("share")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=("post",))
    def reset(self, request, pk=None):
        alert = self.get_object()
        try:
            reset_alert(alert)
        except IntegrityError:
            return Response(
                {"detail": "Такой активный алерт уже существует."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(alert).data)


class PortfolioViewSet(OwnerModelViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(owner=self.request.user).prefetch_related(
            "transactions__share"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TransactionViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = TransactionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Transaction.objects.filter(
            portfolio__owner=self.request.user
        ).select_related("portfolio", "share")


class HistoryView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, share_id):
        share = get_object_or_404(Share, pk=share_id)
        period = request.query_params.get("period", "month")
        if period not in PERIOD_DAYS:
            return Response(
                {"detail": "period must be day, week, month or year"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        prices = list(prices_for_period(share, period))
        return Response(
            {
                "share_id": share.pk,
                "ticker": share.ticker,
                "period": period,
                "change": summarize_prices(prices),
                "results": HistoricalPriceSerializer(prices, many=True).data,
            }
        )


class TradingStrategyViewSet(OwnerModelViewSet):
    serializer_class = TradingStrategySerializer

    def get_queryset(self):
        return TradingStrategy.objects.filter(owner=self.request.user).select_related(
            "share"
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=("post",))
    def run(self, request, pk=None):
        strategy = self.get_object()
        input_serializer = StrategyRunInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            result = run_backtest(strategy, **input_serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            StrategyRunSerializer(result).data, status=status.HTTP_201_CREATED
        )


class StrategyRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StrategyRunSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return StrategyRun.objects.filter(
            strategy__owner=self.request.user
        ).prefetch_related("trades")
