from types import SimpleNamespace

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DataError, IntegrityError
from django.db.models import Count, Exists, F, OuterRef, Q, Window
from django.db.models.functions import RowNumber
from django.shortcuts import get_object_or_404, redirect, render

from rest_framework.throttling import ScopedRateThrottle

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
    StrategyRun,
    StrategyTrade,
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
        {
            "form": form,
            "watchlists": Watchlist.objects.filter(owner=request.user).annotate(
                item_count=Count("items")
            ),
            "alerts": PriceAlert.objects.filter(owner=request.user).select_related(
                "share"
            ),
        },
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
            try:
                share_id = int(request.POST.get("share_id"))
            except (TypeError, ValueError):
                return redirect("dashboard:watchlist-detail", pk=pk)
            deleted_count, _ = watchlist.items.filter(share_id=share_id).delete()
            if deleted_count:
                remaining_memberships = WatchlistItem.objects.filter(
                    share_id=OuterRef("share_id"), watchlist__owner=request.user
                )
                PriceAlert.objects.filter(
                    owner=request.user, share_id=share_id
                ).filter(~Exists(remaining_memberships)).delete()
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
        remaining_memberships = WatchlistItem.objects.filter(
            share_id=OuterRef("share_id"), watchlist__owner=request.user
        ).exclude(watchlist_id=watchlist.pk)
        PriceAlert.objects.filter(
            owner=request.user, share__watchlist_items__watchlist=watchlist
        ).filter(~Exists(remaining_memberships)).delete()
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
            "transactions": Paginator(
                portfolio.transactions.select_related("share"), 50
            ).get_page(request.GET.get("transactions_page")),
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


def _page_links(request, page_param, paginator, current_page):
    page_numbers = sorted(
        {
            1,
            paginator.num_pages,
            *range(
                max(1, current_page - 2),
                min(paginator.num_pages, current_page + 2) + 1,
            ),
        }
    )
    pages = []
    previous_page = None
    for page_number in page_numbers:
        if previous_page is not None and page_number - previous_page > 1:
            pages.append(SimpleNamespace(ellipsis=True))
        query = request.GET.copy()
        query.pop("run", None)
        query[page_param] = str(page_number)
        pages.append(
            SimpleNamespace(
                number=page_number,
                query=query.urlencode(),
                current=page_number == current_page,
                ellipsis=False,
            )
        )
        previous_page = page_number
    return pages


@login_required
def strategies(request):
    form = TradingStrategyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        strategy = form.save(commit=False)
        strategy.owner = request.user
        strategy.save()
        return redirect("dashboard:strategies")
    strategy_paginator = Paginator(
        TradingStrategy.objects.filter(owner=request.user)
        .select_related("share")
        .annotate(run_count=Count("runs")),
        10,
    )
    strategy_page = strategy_paginator.get_page(request.GET.get("strategies_page"))
    strategies_list = list(strategy_page.object_list)
    strategy_pages = _page_links(
        request, "strategies_page", strategy_paginator, strategy_page.number
    )

    run_filter = None
    for strategy in strategies_list:
        page_param = f"runs_{strategy.pk}"
        paginator = Paginator(range(strategy.run_count), 10)
        strategy.run_page = paginator.get_page(request.GET.get(page_param))
        strategy.run_pages = _page_links(
            request, page_param, paginator, strategy.run_page.number
        )
        run_start = (strategy.run_page.number - 1) * 10
        run_end = min(run_start + 10, strategy.run_count)
        if run_start < run_end:
            strategy_runs = Q(
                strategy_id=strategy.pk,
                run_number__gt=run_start,
                run_number__lte=run_end,
            )
            run_filter = (
                strategy_runs if run_filter is None else run_filter | strategy_runs
            )

    runs_by_strategy = {strategy.pk: [] for strategy in strategies_list}
    run_page_numbers = {
        strategy.pk: strategy.run_page.number for strategy in strategies_list
    }
    if run_filter is not None:
        runs = (
            StrategyRun.objects.filter(strategy_id__in=runs_by_strategy).annotate(
                run_number=Window(
                    expression=RowNumber(),
                    partition_by=[F("strategy_id")],
                    order_by=[F("completed_at").desc(), F("pk").desc()],
                )
            )
            .filter(run_filter)
            .annotate(trade_count=Count("trades"))
            .order_by("strategy_id", "-completed_at", "-pk")
        )
        for run in runs:
            query = request.GET.copy()
            query["run"] = str(run.pk)
            query[f"runs_{run.strategy_id}"] = str(run_page_numbers[run.strategy_id])
            run.trades_query = query.urlencode()
            run.is_selected = request.GET.get("run") == str(run.pk)
            if run.is_selected:
                run.selected_trades = list(
                    StrategyTrade.objects.filter(run_id=run.pk).order_by(
                        "executed_at", "pk"
                    )
                )
            runs_by_strategy[run.strategy_id].append(run)

    for strategy in strategies_list:
        strategy.run_page.object_list = runs_by_strategy[strategy.pk]
    return render(
        request,
        "dashboard/strategies.html",
        {
            "form": form,
            "strategies": strategies_list,
            "strategy_pages": strategy_pages,
        },
    )


@login_required
def strategy_run(request, pk):
    strategy = get_object_or_404(TradingStrategy, pk=pk, owner=request.user)
    form = StrategyRunForm(request.POST or None)
    if request.method == "POST":
        throttle = ScopedRateThrottle()
        if not throttle.allow_request(
            request, SimpleNamespace(throttle_scope="backtest")
        ):
            messages.error(
                request, "Достигнут лимит запусков стратегии: 20 в час."
            )
            return redirect("dashboard:strategies")
        if form.is_valid():
            try:
                run_backtest(strategy, **form.cleaned_data)
                messages.success(request, "Симуляция завершена.")
            except ValueError as exc:
                messages.error(request, str(exc))
            except (DataError, OverflowError):
                messages.error(
                    request,
                    "Результаты симуляции превышают допустимый диапазон хранения.",
                )
        else:
            messages.error(request, "Укажите корректный период симуляции.")
    return redirect("dashboard:strategies")
