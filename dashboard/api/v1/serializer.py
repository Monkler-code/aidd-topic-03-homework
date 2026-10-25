"""REST API v1 serializers for share management."""

from rest_framework import serializers

from dashboard.models import Share


class ShareSerializer(serializers.ModelSerializer):
    """Serialize Share model for API responses."""

    class Meta:
        model = Share
        fields = (
            "id",
            "figi",
            "isin",
            "name",
            "ticker",
            "currency",
            "uid",
            "last_price",
            "is_trend_high",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "uid",
            "updated_at",
        )
