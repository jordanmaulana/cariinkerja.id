from datetime import timedelta

from django.utils import timezone

from billing.models import Subscription, SubscriptionStatus, effective_price

ACTIVATION_DAYS = 30
TOTAL_SECONDS = ACTIVATION_DAYS * 86400


class UpgradeNotAllowed(Exception):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def get_active_subscription(profile):
    return (
        Subscription.objects.filter(
            profile=profile,
            status=SubscriptionStatus.ACTIVE,
            expires_at__gt=timezone.now(),
        )
        .select_related("plan")
        .order_by("-created_on")
        .first()
    )


def compute_upgrade_quote(profile, new_plan, *, current_sub=None, at=None):
    """Compute upgrade pricing. Charge full new-plan list price; old credit
    converts into bonus seconds appended to the new 30d window.

    Raises UpgradeNotAllowed for downgrade / same-plan / no-active-sub.
    """
    now = at or timezone.now()
    if current_sub is None:
        current_sub = get_active_subscription(profile)
    if current_sub is None or current_sub.status != SubscriptionStatus.ACTIVE:
        raise UpgradeNotAllowed(
            "no_active_sub", "No active subscription to upgrade from."
        )
    if new_plan.id == current_sub.plan_id:
        raise UpgradeNotAllowed("same_plan", "Already on this plan.")
    if new_plan.price <= current_sub.plan.price:
        raise UpgradeNotAllowed("downgrade", "Downgrade is not available.")

    seconds_remaining = 0.0
    if current_sub.expires_at:
        seconds_remaining = max(0.0, (current_sub.expires_at - now).total_seconds())
    credit_value = current_sub.amount_paid * seconds_remaining / TOTAL_SECONDS
    bonus_seconds = (
        credit_value * TOTAL_SECONDS / new_plan.price if new_plan.price else 0.0
    )
    charge = effective_price(new_plan, profile)
    new_expires_at_estimate = now + timedelta(
        days=ACTIVATION_DAYS, seconds=int(bonus_seconds)
    )
    return {
        "current_plan_id": current_sub.plan_id,
        "new_plan_id": new_plan.id,
        "seconds_remaining": int(seconds_remaining),
        "days_remaining": round(seconds_remaining / 86400, 2),
        "amount_paid_old": current_sub.amount_paid,
        "credit_value": int(round(credit_value)),
        "bonus_seconds": int(bonus_seconds),
        "bonus_days": round(bonus_seconds / 86400, 2),
        "charge": charge,
        "new_expires_at_estimate": new_expires_at_estimate.isoformat(),
    }
