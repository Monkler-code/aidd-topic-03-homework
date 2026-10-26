from django.urls import include, path

from .investment_views import HistoryView
from .router import router

urlpatterns = [
    path("history/<int:share_id>/", HistoryView.as_view(), name="history"),
    path("", include(router.urls)),
]
