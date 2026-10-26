from django.urls import include, path

from dashboard.views import (
    ShareCreateView,
    ShareDeleteView,
    ShareDetailView,
    ShareListView,
    ShareUpdateView,
)
from dashboard.investment_views import (
    alert_reset,
    portfolio_detail,
    portfolio_delete,
    portfolios,
    price_history,
    strategies,
    strategy_run,
    watchlist_detail,
    watchlist_delete,
    watchlists,
)

app_name = "dashboard"

urlpatterns = [
    path("watchlists/", watchlists, name="watchlists"),
    path("watchlists/<int:pk>/", watchlist_detail, name="watchlist-detail"),
    path("watchlists/<int:pk>/delete/", watchlist_delete, name="watchlist-delete"),
    path("alerts/<int:pk>/reset/", alert_reset, name="alert-reset"),
    path("portfolios/", portfolios, name="portfolios"),
    path("portfolios/<int:pk>/", portfolio_detail, name="portfolio-detail"),
    path("portfolios/<int:pk>/delete/", portfolio_delete, name="portfolio-delete"),
    path("history/<int:share_id>/", price_history, name="price-history"),
    path("strategies/", strategies, name="strategies"),
    path("strategies/<int:pk>/run/", strategy_run, name="strategy-run"),
    path("", ShareListView.as_view(), name="index"),
    path("<int:pk>", ShareDetailView.as_view(), name="detail"),
    path("create", ShareCreateView.as_view(), name="create"),
    path("update/<int:pk>", ShareUpdateView.as_view(), name="update"),
    path("delete/<int:pk>", ShareDeleteView.as_view(), name="delete"),
    path("api/", include("dashboard.api.urls")),
]
