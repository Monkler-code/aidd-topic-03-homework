from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from dashboard.models import PriceAlert


def trigger_alerts_for_share(share, current_price):
    """Atomically mark matching active alerts as fired exactly once."""
    price = Decimal(str(current_price))
    now = timezone.now()
    matching_conditions = (
        Q(direction=PriceAlert.Direction.ABOVE, target_price__lte=price)
        | Q(direction=PriceAlert.Direction.BELOW, target_price__gte=price)
    )
    return PriceAlert.objects.filter(
        share=share,
        status=PriceAlert.Status.ACTIVE,
    ).filter(matching_conditions).update(
        status=PriceAlert.Status.TRIGGERED,
        triggered_price=price,
        triggered_at=now,
        notification_sent_at=now,
    )


def reset_alert(alert):
    if alert.status != PriceAlert.Status.TRIGGERED:
        return False
    alert.status = PriceAlert.Status.ACTIVE
    alert.triggered_at = None
    alert.triggered_price = None
    alert.notification_sent_at = None
    alert.save(
        update_fields=(
            "status",
            "triggered_at",
            "triggered_price",
            "notification_sent_at",
        )
    )
    return True
