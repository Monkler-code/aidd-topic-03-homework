"""REST API v1 views for share management."""

from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from dashboard.models import Share

from .serializer import ShareSerializer


class ShareFilter(filters.FilterSet):
    """Filter shares by name and ticker."""

    class Meta:
        model = Share
        fields = ("name", "ticker")


class ShareViewSet(viewsets.ModelViewSet):
    """
    API endpoint for shares:
    - GET /api/v1/shares/ - list shares
    - GET /api/v1/shares/{id}/ - retrieve share
    - POST /api/v1/shares/ - create share
    - PUT /api/v1/shares/{id}/ - update share
    - PATCH /api/v1/shares/{id}/ - partial update
    - DELETE /api/v1/shares/{id}/ - delete share
    """

    serializer_class = ShareSerializer
    queryset = Share.objects.all().order_by("name")
    filter_backends = (OrderingFilter, filters.DjangoFilterBackend, SearchFilter)
    filterset_class = ShareFilter
    ordering_fields = ["name", "ticker", "last_price"]
    search_fields = ["name"]
