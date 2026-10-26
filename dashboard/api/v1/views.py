from django_filters import rest_framework as filters
from django.db.models.deletion import ProtectedError
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from dashboard.models import Share

from .serializer import ShareSerializer


class ShareFilter(filters.FilterSet):
    class Meta:
        model = Share
        fields = ("name", "ticker")


class StaffCanWriteShare(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(
            request.user and request.user.is_staff
        )


class ShareViewSet(viewsets.ModelViewSet):
    serializer_class = ShareSerializer
    queryset = Share.objects.all()
    permission_classes = (StaffCanWriteShare,)
    filter_backends = (OrderingFilter, filters.DjangoFilterBackend, SearchFilter)
    filterset_class = ShareFilter
    ordering_fields = ["name", "ticker"]
    search_fields = ["$name"]

    def destroy(self, request, *args, **kwargs):
        share = self.get_object()
        try:
            self.perform_destroy(share)
        except ProtectedError:
            return Response(
                {"detail": "Нельзя удалить акцию: она используется в истории сделок."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
