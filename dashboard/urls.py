"""Dashboard URL configuration with all new modules."""

from django.urls import include, path

from dashboard.new_views import (
    # Watchlists
    AddShareToWatchlistView,
    CheckAlertsView,
    PriceAlertCreateView,
    PriceAlertResetView,
    PriceHistoryDetailView,
    PriceHistoryListView,
    PortfolioCreateView,
    PortfolioDeleteView,
    PortfolioDetailView,
    PortfolioListView,
    RemoveShareFromWatchlistView,
    RunBacktestView,
    StrategyCreateView,
    StrategyDeleteView,
    StrategyDetailView,
    StrategyListView,
    WatchlistCreateView,
    WatchlistDeleteView,
    WatchlistDetailView,
    WatchlistListView,
    AddTransactionView,
    AddRuleView,
)
from dashboard.views import (
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
)

app_name = "dashboard"

urlpatterns = [
    # Original share routes
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),

    # API routes
    path("api/", include("dashboard.api.urls")),

    # Module 1: Watchlists & Alerts
    path("watchlists/", WatchlistListView.as_view(), name="watchlist-list"),
    path("watchlists/create", WatchlistCreateView.as_view(), name="watchlist-create"),
    path("watchlists/<int:pk>", WatchlistDetailView.as_view(), name="watchlist-detail"),
    path("watchlists/<int:pk>/delete", WatchlistDeleteView.as_view(), name="watchlist-delete"),
    path("watchlists/<int:pk>/add-share", AddShareToWatchlistView.as_view(), name="watchlist-add-share"),
    path("watchlists/<int:pk>/remove-share/<int:item_pk>", RemoveShareFromWatchlistView.as_view(), name="watchlist-remove-share"),
    path("watchlists/<int:pk>/check-alerts", CheckAlertsView.as_view(), name="watchlist-check-alerts"),
    path("alerts/create", PriceAlertCreateView.as_view(), name="alert-create"),
    path("alerts/<int:pk>/reset", PriceAlertResetView.as_view(), name="alert-reset"),

    # Module 2: Portfolio
    path("portfolio/", PortfolioListView.as_view(), name="portfolio-list"),
    path("portfolio/create", PortfolioCreateView.as_view(), name="portfolio-create"),
    path("portfolio/<int:pk>", PortfolioDetailView.as_view(), name="portfolio-detail"),
    path("portfolio/<int:pk>/delete", PortfolioDeleteView.as_view(), name="portfolio-delete"),
    path("portfolio/<int:pk>/transaction", AddTransactionView.as_view(), name="portfolio-add-transaction"),

    # Module 3: Price History
    path("price-history/", PriceHistoryListView.as_view(), name="price-history-list"),
    path("price-history/<int:pk>", PriceHistoryDetailView.as_view(), name="price-history-detail"),

    # Module 4: Strategy Simulator
    path("strategies/", StrategyListView.as_view(), name="strategy-list"),
    path("strategies/create", StrategyCreateView.as_view(), name="strategy-create"),
    path("strategies/<int:pk>", StrategyDetailView.as_view(), name="strategy-detail"),
    path("strategies/<int:pk>/delete", StrategyDeleteView.as_view(), name="strategy-delete"),
    path("strategies/<int:pk>/rule", AddRuleView.as_view(), name="strategy-add-rule"),
    path("strategies/<int:pk>/backtest", RunBacktestView.as_view(), name="strategy-backtest"),
]
