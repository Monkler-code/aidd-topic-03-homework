"""API v2 URL router."""

from rest_framework import routers

from .views import (
    HistoricalPriceViewSet,
    PortfolioViewSet,
    PriceAlertViewSet,
    TradingStrategyViewSet,
    WatchlistViewSet,
)

router = routers.DefaultRouter()
router.register(r"watchlists", WatchlistViewSet, basename="watchlist")
router.register(r"price-alerts", PriceAlertViewSet, basename="price-alert")
router.register(r"portfolios", PortfolioViewSet, basename="portfolio")
router.register(r"historical-prices", HistoricalPriceViewSet, basename="historical-price")
router.register(r"strategies", TradingStrategyViewSet, basename="strategy")
