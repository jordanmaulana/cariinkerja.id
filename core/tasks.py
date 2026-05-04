from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from billing.models import Subscription, SubscriptionStatus
from core.payments.mayar import (
    FAILED_STATUSES,
    PAID_STATUSES,
    MayarError,
    get_payment_status,
)
from core.payments.subscriptions import (
    activate_subscription,
    cancel_pending_subscription,
)

logger = logging.getLogger(__name__)

POLL_WINDOW_HOURS = 48
CHECKOUT_POLL_WINDOW_MINUTES = 10
CHECKOUT_POLL_INTERVAL_SECONDS = 30


@shared_task
def poll_pending_subscriptions():
    cutoff = timezone.now() - timedelta(hours=POLL_WINDOW_HOURS)
    qs = Subscription.objects.filter(
        status=SubscriptionStatus.PENDING,
        created_on__gte=cutoff,
    ).exclude(payment_ref="")
    activated = 0
    cancelled = 0
    errors = 0
    for sub in qs:
        try:
            result = get_payment_status(sub.payment_ref)
        except MayarError as exc:
            errors += 1
            logger.warning("Mayar status check failed for %s: %s", sub.id, exc)
            continue
        status_str = result["status"]
        if status_str in PAID_STATUSES:
            if activate_subscription(sub):
                activated += 1
        elif status_str in FAILED_STATUSES:
            if cancel_pending_subscription(sub):
                cancelled += 1
    logger.info(
        "poll_pending_subscriptions: activated=%d cancelled=%d errors=%d",
        activated,
        cancelled,
        errors,
    )
    return {"activated": activated, "cancelled": cancelled, "errors": errors}


@shared_task(bind=True)
def poll_subscription_after_checkout(self, subscription_id: str):
    """Aggressively poll Mayar for a single subscription post-checkout.

    Self-reschedules every CHECKOUT_POLL_INTERVAL_SECONDS until the
    subscription leaves PENDING or CHECKOUT_POLL_WINDOW_MINUTES elapses
    since checkout. Webhook is the primary path; this is the fallback.
    """
    sub = Subscription.objects.filter(pk=subscription_id).first()
    if sub is None:
        logger.info("poll_after_checkout: sub=%s missing, drop", subscription_id)
        return
    if sub.status != SubscriptionStatus.PENDING:
        logger.info("poll_after_checkout: sub=%s status=%s, stop", sub.id, sub.status)
        return
    if not sub.payment_ref:
        logger.info("poll_after_checkout: sub=%s no payment_ref, drop", sub.id)
        return

    deadline = sub.created_on + timedelta(minutes=CHECKOUT_POLL_WINDOW_MINUTES)
    if timezone.now() >= deadline:
        logger.info("poll_after_checkout: sub=%s window elapsed, stop", sub.id)
        return

    try:
        result = get_payment_status(sub.payment_ref)
    except MayarError as exc:
        logger.warning("poll_after_checkout: sub=%s mayar error %s, retry", sub.id, exc)
        raise self.retry(countdown=CHECKOUT_POLL_INTERVAL_SECONDS, max_retries=None)

    status_str = result["status"]
    if status_str in PAID_STATUSES:
        activate_subscription(sub)
        return
    if status_str in FAILED_STATUSES:
        cancel_pending_subscription(sub)
        return

    self.apply_async(args=[subscription_id], countdown=CHECKOUT_POLL_INTERVAL_SECONDS)
