"""Django admin configuration for dashboard models."""

from django.contrib import admin

from .models import Share


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    """Admin interface for Share model."""

    list_display = ("ticker", "name", "figi", "currency", "last_price", "is_trend_high")
    list_filter = ("currency", "is_trend_high")
    search_fields = ("figi", "isin", "name", "ticker")
    readonly_fields = ("figi", "isin", "uid", "updated_at")
    fields = (
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
