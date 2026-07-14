import logging
from datetime import timedelta

from django.utils import timezone

from assessment.tasks import crawl_and_assess_preference
from billing.models import Subscription, SubscriptionStatus
from core.realtime import publish, user_channel
from jobs.url_builders import build_crawl_urls
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference

logger = logging.getLogger(__name__)

ACTIVATION_DAYS = 30


TOTAL_SECONDS = ACTIVATION_DAYS * 86400


def activate_subscription(sub: Subscription) -> bool:
    """Flip Subscription PENDING→ACTIVE and unlock Preferences. Idempotent.

    For upgrade subs (`replaces` set): grants bonus_seconds derived from the
    old sub's unused value, marks the old sub REPLACED, and skips preference
    unlock (preferences already RUNNING under the old plan).

    Returns True if a transition happened, False if already ACTIVE.
    """
    logger.info(
        "activate_subscription: sub=%s status=%s payment_ref=%s replaces=%s",
        sub.id,
        sub.status,
        sub.payment_ref,
        sub.replaces_id,
    )
    if sub.status == SubscriptionStatus.ACTIVE:
        logger.info("activate_subscription: sub=%s already ACTIVE, skip", sub.id)
        return False
    now = timezone.now()
    bonus_seconds = 0
    replaces_id = sub.replaces_id
    if replaces_id:
        old = Subscription.objects.select_related("plan").filter(pk=replaces_id).first()
        if old is not None and old.expires_at and sub.plan.price:
            seconds_remaining = max(0.0, (old.expires_at - now).total_seconds())
            credit_value = old.amount_paid * seconds_remaining / TOTAL_SECONDS
            bonus_seconds = int(credit_value * TOTAL_SECONDS / sub.plan.price)
        Subscription.objects.filter(
            pk=replaces_id, status=SubscriptionStatus.ACTIVE
        ).update(
            status=SubscriptionStatus.REPLACED,
            expires_at=now,
            updated_on=now,
        )
    sub.status = SubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timedelta(days=ACTIVATION_DAYS, seconds=bonus_seconds)
    sub.save(update_fields=["status", "started_at", "expires_at", "updated_on"])
    if replaces_id:
        logger.info(
            "activate_subscription: sub=%s upgrade ACTIVE bonus_seconds=%d expires_at=%s",
            sub.id,
            bonus_seconds,
            sub.expires_at.isoformat(),
        )
    else:
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
        # The post-payment crawl is the only crawl a paid user gets, so guarantee
        # it: backfill crawl_urls for any pref that reached WAITING_PAYMENT without
        # them (admin manual path, whitespace title, etc.), and never skip silently.
        for pref in Preference.objects.filter(id__in=pref_ids):
            if not pref.crawl_urls and pref.title:
                pref.crawl_urls = build_crawl_urls(
                    pref.title, pref.job_type, pref.remote_option
                )
                pref.save(update_fields=["crawl_urls", "updated_on"])
            if pref.crawl_urls:
                crawl_and_assess_preference.delay(pref.id)
                logger.info(
                    "activate_subscription: sub=%s queued crawl preference=%s",
                    sub.id,
                    pref.id,
                )
            else:
                logger.warning(
                    "activate_subscription: sub=%s preference=%s has no crawl_urls "
                    "(no usable title); crawl skipped",
                    sub.id,
                    pref.id,
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
                "replaces_id": replaces_id,
                "bonus_seconds": bonus_seconds,
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
