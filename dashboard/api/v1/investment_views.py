from django.db import DataError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from dashboard.api.v1.investment_serializers import (
    HistoricalPriceSerializer,
    PortfolioSerializer,
    PriceAlertSerializer,
    StrategyRunInputSerializer,
    StrategyRunListSerializer,
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
from dashboard.services.alerts import (
    delete_alerts_without_watchlist_membership,
    reset_alert,
)
from dashboard.services.backtesting import run_backtest
from dashboard.services.history import PERIOD_DAYS, prices_for_period, summarize_prices
from dashboard.services.portfolio import get_portfolio_summaries


class IntegrityConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Запись конфликтует с существующими данными."
    default_code = "conflict"


class OwnerModelViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)


class ConflictOnIntegrityViewSet(OwnerModelViewSet):
    def _save_with_conflict_handling(self, serializer, **kwargs):
        try:
            with transaction.atomic():
                serializer.save(**kwargs)
        except IntegrityError as exc:
            raise IntegrityConflict from exc

    def perform_create(self, serializer):
        self._save_with_conflict_handling(serializer, owner=self.request.user)

    def perform_update(self, serializer):
        self._save_with_conflict_handling(serializer)


class WatchlistViewSet(ConflictOnIntegrityViewSet):
    serializer_class = WatchlistSerializer

    def get_queryset(self):
        return Watchlist.objects.filter(owner=self.request.user).prefetch_related(
            "shares"
        )

    def perform_destroy(self, instance):
        with transaction.atomic():
            share_ids = list(instance.items.values_list("share_id", flat=True))
            owner_id = instance.owner_id
            instance.delete()
            delete_alerts_without_watchlist_membership(owner_id, share_ids)


class PriceAlertViewSet(ConflictOnIntegrityViewSet):
    serializer_class = PriceAlertSerializer

    def get_queryset(self):
        return PriceAlert.objects.filter(owner=self.request.user).select_related("share")

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


class PortfolioViewSet(ConflictOnIntegrityViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(owner=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is None:
            portfolios = list(queryset)
            summaries = get_portfolio_summaries(portfolios)
            serializer = self.get_serializer(
                portfolios,
                many=True,
                context={
                    **self.get_serializer_context(),
                    "portfolio_summaries": summaries,
                },
            )
            return Response(serializer.data)

        portfolios = list(page)
        summaries = get_portfolio_summaries(portfolios)
        serializer = self.get_serializer(
            portfolios,
            many=True,
            context={
                **self.get_serializer_context(),
                "portfolio_summaries": summaries,
            },
        )
        return self.get_paginated_response(serializer.data)


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

    def destroy(self, request, *args, **kwargs):
        strategy = self.get_object()
        try:
            self.perform_destroy(strategy)
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "Нельзя удалить стратегию, пока у нее есть сохраненные запуски."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_throttles(self):
        throttles = super().get_throttles()
        if getattr(self, "action", None) == "run":
            self.throttle_scope = "backtest"
            throttles.append(ScopedRateThrottle())
        return throttles

    @action(detail=True, methods=("post",))
    def run(self, request, pk=None):
        strategy = self.get_object()
        input_serializer = StrategyRunInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        try:
            result = run_backtest(strategy, **input_serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (DataError, OverflowError):
            return Response(
                {
                    "detail": (
                        "Результаты симуляции превышают допустимый диапазон хранения."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            StrategyRunSerializer(result).data, status=status.HTTP_201_CREATED
        )


class StrategyRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StrategyRunSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "list":
            return StrategyRunListSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = StrategyRun.objects.filter(strategy__owner=self.request.user)
        if self.action != "list":
            queryset = queryset.prefetch_related("trades")
        return queryset
