"""Views for new investment modules."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
    View,
)

from dashboard.models import (
    HistoricalPrice,
    Portfolio,
    PriceAlert,
    Share,
    StrategyRule,
    StrategyTrade,
    TradingStrategy,
    Watchlist,
    WatchlistItem,
)
from dashboard.services.alert_checker import check_price_alerts
from dashboard.services.backtester import StrategyBacktester
from dashboard.services.portfolio import PortfolioCalculator
from dashboard.services.price_history import PriceHistoryService
from dashboard.services.watchlists import PriceAlertService, WatchlistService


# =============================================================================
# MODULE 1: Watchlists & Alerts
# =============================================================================


class WatchlistListView(LoginRequiredMixin, ListView):
    """List user's watchlists."""

    model = Watchlist
    template_name = "dashboard/watchlist/list.html"
    context_object_name = "watchlists"

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user).prefetch_related("items__share")


class WatchlistDetailView(LoginRequiredMixin, View):
    """Detail view for a watchlist."""

    def get(self, request, pk):
        watchlist = get_object_or_404(Watchlist, pk=pk, user=request.user)
        items = WatchlistService.get_watchlist_with_prices(watchlist)
        alerts = PriceAlertService.get_user_alerts(request.user)
        shares = Share.objects.all()
        return render(request, "dashboard/watchlist/detail.html", {
            "watchlist": watchlist,
            "items": items,
            "alerts": alerts,
            "shares": shares,
        })


class WatchlistCreateView(LoginRequiredMixin, CreateView):
    """Create a new watchlist."""

    model = Watchlist
    template_name = "dashboard/watchlist/form.html"
    fields = ["name"]
    success_url = reverse_lazy("dashboard:watchlist-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class WatchlistDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a watchlist."""

    model = Watchlist
    template_name = "dashboard/watchlist/delete.html"
    success_url = reverse_lazy("dashboard:watchlist-list")

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)


class AddShareToWatchlistView(LoginRequiredMixin, View):
    """Add a share to a watchlist."""

    def post(self, request, pk):
        watchlist = get_object_or_404(Watchlist, pk=pk, user=request.user)
        share_id = request.POST.get("share_id")
        if share_id:
            share = get_object_or_404(Share, id=share_id)
            WatchlistService.add_share_to_watchlist(watchlist, share)
        return redirect("dashboard:watchlist-detail", pk=watchlist.pk)


class RemoveShareFromWatchlistView(LoginRequiredMixin, View):
    """Remove a share from a watchlist."""

    def post(self, request, pk, item_pk):
        watchlist = get_object_or_404(Watchlist, pk=pk, user=request.user)
        item = get_object_or_404(WatchlistItem, pk=item_pk, watchlist=watchlist)
        WatchlistService.remove_share_from_watchlist(watchlist, item.share)
        return redirect("dashboard:watchlist-detail", pk=watchlist.pk)


class PriceAlertCreateView(LoginRequiredMixin, View):
    """Create a new price alert."""

    def post(self, request):
        watchlist_item_id = request.POST.get("watchlist_item_id")
        share_id = request.POST.get("share_id")
        alert_type = request.POST.get("alert_type")
        target_price = request.POST.get("target_price")

        if not all([watchlist_item_id, share_id, alert_type, target_price]):
            return redirect("dashboard:watchlist-detail", pk=request.POST.get("watchlist_pk"))

        try:
            watchlist_item = WatchlistItem.objects.get(
                id=watchlist_item_id,
                watchlist__user=request.user,
            )
            share = Share.objects.get(id=share_id)
            PriceAlertService.create_alert(
                watchlist_item=watchlist_item,
                share=share,
                alert_type=alert_type,
                target_price=float(target_price),
            )
        except (WatchlistItem.DoesNotExist, Share.DoesNotExist, ValueError):
            pass

        return redirect("dashboard:watchlist-detail", pk=request.POST.get("watchlist_pk"))


class PriceAlertResetView(LoginRequiredMixin, View):
    """Reset a triggered alert."""

    def post(self, request, pk):
        alert = get_object_or_404(
            PriceAlert,
            pk=pk,
            watchlist_item__watchlist__user=request.user,
        )
        PriceAlertService.reset_alert(alert)
        return redirect("dashboard:watchlist-detail", pk=alert.watchlist_item.watchlist.pk)


class CheckAlertsView(LoginRequiredMixin, View):
    """Check all alerts against current prices."""

    def post(self, request):
        triggered = check_price_alerts()
        return redirect("dashboard:watchlist-list")


# =============================================================================
# MODULE 2: Portfolio
# =============================================================================


class PortfolioListView(LoginRequiredMixin, ListView):
    """List user's portfolios."""

    model = Portfolio
    template_name = "dashboard/portfolio/list.html"
    context_object_name = "portfolios"

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


class PortfolioDetailView(LoginRequiredMixin, View):
    """Detail view for a portfolio."""

    def get(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        summary = PortfolioCalculator.get_portfolio_summary(portfolio)
        transactions = PortfolioCalculator.get_transaction_history(portfolio)
        shares = Share.objects.all()
        return render(request, "dashboard/portfolio/detail.html", {
            "portfolio": portfolio,
            "summary": summary,
            "transactions": transactions,
            "shares": shares,
        })


class PortfolioCreateView(LoginRequiredMixin, CreateView):
    """Create a new portfolio."""

    model = Portfolio
    template_name = "dashboard/portfolio/form.html"
    fields = ["name"]
    success_url = reverse_lazy("dashboard:portfolio-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class PortfolioDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a portfolio."""

    model = Portfolio
    template_name = "dashboard/portfolio/delete.html"
    success_url = reverse_lazy("dashboard:portfolio-list")

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)


class AddTransactionView(LoginRequiredMixin, View):
    """Add a transaction to a portfolio."""

    def post(self, request, pk):
        portfolio = get_object_or_404(Portfolio, pk=pk, user=request.user)
        share_id = request.POST.get("share_id")
        transaction_type = request.POST.get("transaction_type")
        quantity = request.POST.get("quantity")
        price = request.POST.get("price")
        commission = request.POST.get("commission", 0)

        if not all([share_id, transaction_type, quantity, price]):
            return redirect("dashboard:portfolio-detail", pk=portfolio.pk)

        try:
            share = Share.objects.get(id=share_id)
            PortfolioCalculator.add_transaction(
                portfolio=portfolio,
                share=share,
                transaction_type=transaction_type,
                quantity=int(quantity),
                price=float(price),
                commission=float(commission),
            )
        except (Share.DoesNotExist, ValueError):
            pass

        return redirect("dashboard:portfolio-detail", pk=portfolio.pk)


# =============================================================================
# MODULE 3: Price History
# =============================================================================


class PriceHistoryListView(LoginRequiredMixin, ListView):
    """List shares with price history."""

    model = Share
    template_name = "dashboard/price_history/list.html"
    context_object_name = "shares"

    def get_queryset(self):
        return Share.objects.prefetch_related("historical_prices")


class PriceHistoryDetailView(LoginRequiredMixin, View):
    """Detail view for a share's price history."""

    def get(self, request, pk):
        share = get_object_or_404(Share, pk=pk)
        days = int(request.GET.get("days", 180))
        chart_data = PriceHistoryService.build_price_chart_data(share, days)
        period_change = PriceHistoryService.calculate_period_change(share, days)
        history = PriceHistoryService.get_price_history(share)

        return render(request, "dashboard/price_history/detail.html", {
            "share": share,
            "chart_data": chart_data,
            "period_change": period_change,
            "history": history,
            "days": days,
        })


# =============================================================================
# MODULE 4: Strategy Simulator
# =============================================================================


class StrategyListView(LoginRequiredMixin, ListView):
    """List user's trading strategies."""

    model = TradingStrategy
    template_name = "dashboard/strategy/list.html"
    context_object_name = "strategies"

    def get_queryset(self):
        return TradingStrategy.objects.filter(user=self.request.user)


class StrategyDetailView(LoginRequiredMixin, View):
    """Detail view for a strategy."""

    def get(self, request, pk):
        strategy = get_object_or_404(TradingStrategy, pk=pk, user=request.user)
        rules = strategy.rules.all()
        trades = strategy.trades.all()
        shares = Share.objects.all()
        return render(request, "dashboard/strategy/detail.html", {
            "strategy": strategy,
            "rules": rules,
            "trades": trades,
            "shares": shares,
        })


class StrategyCreateView(LoginRequiredMixin, CreateView):
    """Create a new trading strategy."""

    model = TradingStrategy
    template_name = "dashboard/strategy/form.html"
    fields = ["name", "description"]
    success_url = reverse_lazy("dashboard:strategy-list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class StrategyDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a trading strategy."""

    model = TradingStrategy
    template_name = "dashboard/strategy/delete.html"
    success_url = reverse_lazy("dashboard:strategy-list")

    def get_queryset(self):
        return TradingStrategy.objects.filter(user=self.request.user)


class AddRuleView(LoginRequiredMixin, View):
    """Add a rule to a strategy."""

    def post(self, request, pk):
        strategy = get_object_or_404(TradingStrategy, pk=pk, user=request.user)
        condition_field = request.POST.get("condition_field")
        condition_operator = request.POST.get("condition_operator")
        condition_value = request.POST.get("condition_value")
        action = request.POST.get("action")
        priority = request.POST.get("priority", 0)

        if all([condition_field, condition_operator, condition_value, action]):
            StrategyRule.objects.create(
                strategy=strategy,
                condition_field=condition_field,
                condition_operator=condition_operator,
                condition_value=float(condition_value),
                action=action,
                priority=int(priority),
            )

        return redirect("dashboard:strategy-detail", pk=strategy.pk)


class RunBacktestView(LoginRequiredMixin, View):
    """Run a backtest for a strategy."""

    def post(self, request, pk):
        strategy = get_object_or_404(TradingStrategy, pk=pk, user=request.user)
        share_id = request.POST.get("share_id")
        days = int(request.POST.get("days", 365))

        if not share_id:
            return redirect("dashboard:strategy-detail", pk=strategy.pk)

        try:
            share = Share.objects.get(id=share_id)
            backtester = StrategyBacktester(strategy)
            trades = backtester.run_backtest(share, days)
            metrics = StrategyBacktester.calculate_metrics(trades, backtester.virtual_cash)

            return render(request, "dashboard/strategy/backtest_result.html", {
                "strategy": strategy,
                "metrics": metrics,
                "trades": trades,
            })
        except Share.DoesNotExist:
            return redirect("dashboard:strategy-detail", pk=strategy.pk)
