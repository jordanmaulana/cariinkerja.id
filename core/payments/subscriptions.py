import logging
from datetime import timedelta

from django.utils import timezone

from assessment.tasks import crawl_and_assess_preference
from billing.models import Subscription, SubscriptionStatus
from core.realtime import publish, user_channel
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference

logger = logging.getLogger(__name__)

ACTIVATION_DAYS = 30


def activate_subscription(sub: Subscription) -> bool:
    """Flip Subscription PENDING→ACTIVE and unlock Preferences. Idempotent.

    Returns True if a transition happened, False if already ACTIVE.
    """
    logger.info(
        "activate_subscription: sub=%s status=%s payment_ref=%s",
        sub.id,
        sub.status,
        sub.payment_ref,
    )
    if sub.status == SubscriptionStatus.ACTIVE:
        logger.info("activate_subscription: sub=%s already ACTIVE, skip", sub.id)
        return False
    now = timezone.now()
    sub.status = SubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timedelta(days=ACTIVATION_DAYS)
    sub.save(update_fields=["status", "started_at", "expires_at", "updated_on"])
    pending_prefs = Preference.objects.filter(
        profile=sub.profile,
        status=PreferenceStatus.WAITING_PAYMENT,
    )
    pref_ids = list(pending_prefs.values_list("id", flat=True))
    unlocked = pending_prefs.update(status=PreferenceStatus.RUNNING, updated_on=now)
    logger.info(
        "activate_subscription: sub=%s ACTIVE expires_at=%s preferences_unlocked=%d",
        sub.id,
        sub.expires_at.isoformat(),
        unlocked,
    )
    crawlable = (
        Preference.objects.filter(id__in=pref_ids)
        .exclude(crawl_url__isnull=True)
        .exclude(crawl_url="")
        .exclude(crawl_source__isnull=True)
        .exclude(crawl_source="")
        .values_list("id", flat=True)
    )
    for pid in crawlable:
        crawl_and_assess_preference.delay(pid)
        logger.info(
            "activate_subscription: sub=%s queued crawl preference=%s", sub.id, pid
        )
    user_id = getattr(getattr(sub.profile, "user", None), "id", None)
    if user_id is not None:
        publish(
            user_channel(user_id),
            {
                "event": "subscription.activated",
                "subscription_id": sub.id,
                "status": sub.status,
                "expires_at": sub.expires_at.isoformat(),
                "plan": sub.plan.name,
            },
        )
    return True


def cancel_pending_subscription(sub: Subscription) -> bool:
    logger.info("cancel_pending_subscription: sub=%s status=%s", sub.id, sub.status)
    if sub.status != SubscriptionStatus.PENDING:
        logger.info("cancel_pending_subscription: sub=%s not PENDING, skip", sub.id)
        return False
    sub.status = SubscriptionStatus.CANCELLED
    sub.save(update_fields=["status", "updated_on"])
    logger.info("cancel_pending_subscription: sub=%s CANCELLED", sub.id)
    return True
