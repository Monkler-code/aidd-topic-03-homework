from rest_framework import routers

from .investment_views import (
    PortfolioViewSet,
    PriceAlertViewSet,
    StrategyRunViewSet,
    TradingStrategyViewSet,
    TransactionViewSet,
    WatchlistViewSet,
)
from .views import ShareViewSet

router = routers.DefaultRouter()
router.register(r"shares", ShareViewSet)
router.register(r"watchlists", WatchlistViewSet, basename="watchlist")
router.register(r"alerts", PriceAlertViewSet, basename="price-alert")
router.register(r"portfolios", PortfolioViewSet, basename="portfolio")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"strategies", TradingStrategyViewSet, basename="strategy")
router.register(r"strategy-runs", StrategyRunViewSet, basename="strategy-run")
