from django.contrib import admin

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


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("figi", "isin", "name", "ticker", "currency")
    search_fields = ("figi", "isin", "name", "ticker")
    fields = (
        "figi",
        "isin",
        "name",
        "ticker",
        "currency",
        "uid",
        "last_price",
        "is_trend_high",
    )


admin.site.register(
    (Watchlist, WatchlistItem, PriceAlert, Portfolio, Transaction, HistoricalPrice,
     TradingStrategy, StrategyRun, StrategyTrade)
)
