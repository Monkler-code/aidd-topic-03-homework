from rest_framework import serializers

from dashboard.models import Share


class ShareSerializer(serializers.ModelSerializer):
    uid = serializers.CharField(required=False)
    # Keep the existing JSON number representation while storing prices as Decimal.
    last_price = serializers.FloatField(read_only=True, allow_null=True)

    class Meta:
        model = Share
        fields = (
            "id",
            "figi",
            "uid",
            "isin",
            "name",
            "ticker",
            "currency",
            "last_price",
            "is_trend_high",
            "updated_at",
        )
        read_only_fields = ("is_trend_high", "updated_at")

    def validate(self, attrs):
        if self.instance is None and not attrs.get("uid"):
            raise serializers.ValidationError({"uid": "This field is required."})
        return attrs
