from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from dashboard.forms import (
    PortfolioForm,
    PriceAlertForm,
    StrategyRunForm,
    TradingStrategyForm,
    TransactionForm,
    WatchlistForm,
    WatchlistShareForm,
)
from dashboard.models import (
    Portfolio,
    PriceAlert,
    Share,
    TradingStrategy,
    Watchlist,
    WatchlistItem,
)
from dashboard.services.alerts import reset_alert
from dashboard.services.backtesting import run_backtest
from dashboard.services.history import (
    PERIOD_DAYS,
    prices_for_period,
    render_price_graph,
    summarize_prices,
)
from dashboard.services.portfolio import get_portfolio_summary, record_transaction


@login_required
def watchlists(request):
    form = WatchlistForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        watchlist = form.save(commit=False)
        watchlist.owner = request.user
        try:
            watchlist.save()
            return redirect("dashboard:watchlist-detail", pk=watchlist.pk)
        except IntegrityError:
            form.add_error("name", "У вас уже есть список с таким названием.")
    return render(
        request,
        "dashboard/watchlists.html",
        {"form": form, "watchlists": Watchlist.objects.filter(owner=request.user)},
    )


@login_required
def watchlist_detail(request, pk):
    watchlist = get_object_or_404(Watchlist, pk=pk, owner=request.user)
    rename_form = WatchlistForm(instance=watchlist)
    share_form = WatchlistShareForm()
    alert_form = PriceAlertForm()
    alert_form.fields["share"].queryset = watchlist.shares.order_by("ticker")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "rename":
            rename_form = WatchlistForm(request.POST, instance=watchlist)
            if rename_form.is_valid():
                try:
                    rename_form.save()
                    return redirect("dashboard:watchlist-detail", pk=pk)
                except IntegrityError:
                    rename_form.add_error("name", "Название списка уже используется.")
        elif action == "delete-alert":
            PriceAlert.objects.filter(
                pk=request.POST.get("alert_id"),
                owner=request.user,
                share__watchlist_items__watchlist=watchlist,
            ).delete()
            return redirect("dashboard:watchlist-detail", pk=pk)
        elif action == "add-share":
            share_form = WatchlistShareForm(request.POST)
            if share_form.is_valid():
                WatchlistItem.objects.get_or_create(
                    watchlist=watchlist, share=share_form.cleaned_data["share"]
                )
                return redirect("dashboard:watchlist-detail", pk=pk)
        elif action == "remove-share":
            watchlist.items.filter(share_id=request.POST.get("share_id")).delete()
            return redirect("dashboard:watchlist-detail", pk=pk)
        elif action == "add-alert":
            alert_form = PriceAlertForm(request.POST)
            alert_form.fields["share"].queryset = watchlist.shares.order_by("ticker")
            alert_form.instance.owner = request.user
            if alert_form.is_valid():
                alert = alert_form.save(commit=False)
                alert.owner = request.user
                try:
                    alert.save()
                    return redirect("dashboard:watchlist-detail", pk=pk)
                except IntegrityError:
                    alert_form.add_error(None, "Такой активный алерт уже существует.")

    return render(
        request,
        "dashboard/watchlist_detail.html",
        {
            "watchlist": watchlist,
            "rename_form": rename_form,
            "items": watchlist.items.select_related("share"),
            "share_form": share_form,
            "alert_form": alert_form,
            "alerts": PriceAlert.objects.filter(
                owner=request.user, share__watchlist_items__watchlist=watchlist
            ).select_related("share").distinct(),
        },
    )


@login_required
def watchlist_delete(request, pk):
    if request.method == "POST":
        watchlist = get_object_or_404(Watchlist, pk=pk, owner=request.user)
        watchlist.delete()
    return redirect("dashboard:watchlists")


@login_required
def alert_reset(request, pk):
    if request.method == "POST":
        alert = get_object_or_404(PriceAlert, pk=pk, owner=request.user)
        watchlist_id = request.POST.get("watchlist_id")
        try:
            reset_alert(alert)
            messages.success(request, "Алерт снова активен.")
        except IntegrityError:
            messages.error(request, "Такой активный алерт уже существует.")
        if watchlist_id and Watchlist.objects.filter(
            pk=watchlist_id, owner=request.user
        ).exists():
            return redirect("dashboard:watchlist-detail", pk=watchlist_id)
        return redirect("dashboard:watchlists")
    return redirect("dashboard:watchlists")


@login_required
def portfolios(request):
    form = PortfolioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        portfolio = form.save(commit=False)
        portfolio.owner = request.user
        try:
            portfolio.save()
            return redirect("dashboard:portfolio-detail", pk=portfolio.pk)
        except IntegrityError:
            form.add_error("name", "У вас уже есть портфель с таким названием.")
    return render(
        request,
        "dashboard/portfolios.html",
        {"form": form, "portfolios": Portfolio.objects.filter(owner=request.user)},
    )


@login_required
def portfolio_delete(request, pk):
    if request.method == "POST":
        portfolio = get_object_or_404(Portfolio, pk=pk, owner=request.user)
        portfolio.delete()
    return redirect("dashboard:portfolios")


@login_required
def portfolio_detail(request, pk):
    portfolio = get_object_or_404(Portfolio, pk=pk, owner=request.user)
    form = TransactionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            record_transaction(
                portfolio=portfolio,
                **form.cleaned_data,
            )
            return redirect("dashboard:portfolio-detail", pk=pk)
        except ValueError as exc:
            form.add_error(None, str(exc))
    return render(
        request,
        "dashboard/portfolio_detail.html",
        {
            "portfolio": portfolio,
            "form": form,
            "summary": get_portfolio_summary(portfolio),
            "transactions": portfolio.transactions.select_related("share"),
        },
    )


def price_history(request, share_id):
    share = get_object_or_404(Share, pk=share_id)
    period = request.GET.get("period", "month")
    if period not in PERIOD_DAYS:
        period = "month"
    prices = list(prices_for_period(share, period))
    return render(
        request,
        "dashboard/price_history.html",
        {
            "share": share,
            "period": period,
            "prices": prices,
            "summary": summarize_prices(prices),
            "plot_div": render_price_graph(prices),
        },
    )


@login_required
def strategies(request):
    form = TradingStrategyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        strategy = form.save(commit=False)
        strategy.owner = request.user
        strategy.save()
        return redirect("dashboard:strategies")
    strategies_list = TradingStrategy.objects.filter(owner=request.user).select_related(
        "share"
    ).prefetch_related("runs__trades")
    return render(
        request,
        "dashboard/strategies.html",
        {"form": form, "strategies": strategies_list},
    )


@login_required
def strategy_run(request, pk):
    strategy = get_object_or_404(TradingStrategy, pk=pk, owner=request.user)
    form = StrategyRunForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            run_backtest(strategy, **form.cleaned_data)
            messages.success(request, "Симуляция завершена.")
        except ValueError as exc:
            messages.error(request, str(exc))
    elif request.method == "POST":
        messages.error(request, "Укажите корректный период симуляции.")
    return redirect("dashboard:strategies")
