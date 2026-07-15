from datetime import timedelta

from django.utils import timezone

from billing.models import Subscription, SubscriptionStatus, effective_price


def prorate_upgrade(old_sub, new_plan, now):
    """Convert an old sub's unused value into bonus seconds on the new plan.

    Returns (seconds_remaining, credit_value, bonus_seconds).

    The two durations are distinct and must not be collapsed into one constant:
    the old plan sets the rate the credit was bought at, the new plan sets the
    rate it is spent at. They only cancel out while every plan is 30 days.

    `seconds_remaining` can exceed the old plan's own duration when that sub
    carried bonus seconds from a prior upgrade, so `credit_value` can exceed
    `amount_paid`. That is existing, intended behaviour.
    """
    if old_sub is None or not old_sub.expires_at or not new_plan.price:
        return 0.0, 0.0, 0.0
    seconds_remaining = max(0.0, (old_sub.expires_at - now).total_seconds())
    credit_value = (
        old_sub.amount_paid * seconds_remaining / (old_sub.plan.duration_days * 86400)
    )
    bonus_seconds = credit_value * (new_plan.duration_days * 86400) / new_plan.price
    return seconds_remaining, credit_value, bonus_seconds


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
    converts into bonus seconds appended to the new plan's window.

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
    if new_plan.preference_limit <= current_sub.plan.preference_limit:
        raise UpgradeNotAllowed("downgrade", "Downgrade is not available.")

    seconds_remaining, credit_value, bonus_seconds = prorate_upgrade(
        current_sub, new_plan, now
    )
    charge = effective_price(new_plan, profile)
    new_expires_at_estimate = now + timedelta(
        days=new_plan.duration_days, seconds=int(bonus_seconds)
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
