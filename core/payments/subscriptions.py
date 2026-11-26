import logging
from datetime import timedelta

from django.utils import timezone

from assessment.tasks import crawl_and_assess_preference
from billing.models import Subscription, SubscriptionStatus
from billing.upgrades import prorate_upgrade
from core.realtime import publish, user_channel
from jobs.url_builders import build_crawl_urls
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference

logger = logging.getLogger(__name__)

# Unpaid (WAITING_PAYMENT) and lapsed (EXPIRED) searches both come back on payment.
RESUMABLE = (PreferenceStatus.WAITING_PAYMENT, PreferenceStatus.EXPIRED)


def _resume_preferences(sub: Subscription) -> int:
    """Flip the profile's resumable Preferences to RUNNING and queue a crawl each.

    Capped at the plan's free slots (limit minus already-RUNNING), most recently
    edited first, so renewing on a smaller plan can't keep a bigger plan's
    searches; the rest stay EXPIRED. Whitelisted profiles aren't capped.
    """
    prefs = Preference.objects.filter(profile=sub.profile)
    resumable = prefs.filter(status__in=RESUMABLE).order_by(
        "-updated_on", "-created_on"
    )
    if not sub.profile.whitelist:
        running = prefs.filter(status=PreferenceStatus.RUNNING).count()
        resumable = resumable[: max(sub.plan.preference_limit - running, 0)]
    resumed = 0
    for pref in resumable:
        # The post-payment crawl is the only crawl a paid user gets, so guarantee
        # it: backfill crawl_urls for any pref that got here without them (admin
        # manual path, whitespace title, etc.), and never skip silently.
        if not pref.crawl_urls and pref.title:
            pref.crawl_urls = build_crawl_urls(
                pref.title, pref.job_type, pref.remote_option
            )
        pref.status = PreferenceStatus.RUNNING
        pref.save(update_fields=["crawl_urls", "status", "updated_on"])
        resumed += 1
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
    return resumed


def activate_subscription(sub: Subscription) -> bool:
    """Flip Subscription PENDING→ACTIVE and resume Preferences. Idempotent.

    Runs for `sub.plan.duration_days`. For upgrade subs (`replaces` set):
    grants bonus_seconds derived from the old sub's unused value and marks the
    old sub REPLACED. Either way, WAITING_PAYMENT/EXPIRED preferences resume up
    to the plan's free slots (see `_resume_preferences`); RUNNING ones are left
    alone.

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
        _, _, raw_bonus = prorate_upgrade(old, sub.plan, now)
        bonus_seconds = int(raw_bonus)
        Subscription.objects.filter(
            pk=replaces_id, status=SubscriptionStatus.ACTIVE
        ).update(
            status=SubscriptionStatus.REPLACED,
            expires_at=now,
            updated_on=now,
        )
    sub.status = SubscriptionStatus.ACTIVE
    sub.started_at = now
    sub.expires_at = now + timedelta(days=sub.plan.duration_days, seconds=bonus_seconds)
    sub.save(update_fields=["status", "started_at", "expires_at", "updated_on"])
    resumed = _resume_preferences(sub)
    logger.info(
        "activate_subscription: sub=%s ACTIVE expires_at=%s bonus_seconds=%d "
        "preferences_resumed=%d",
        sub.id,
        sub.expires_at.isoformat(),
        bonus_seconds,
        resumed,
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
