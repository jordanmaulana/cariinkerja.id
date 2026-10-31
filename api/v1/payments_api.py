import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from billing.models import Subscription, SubscriptionStatus
from core.payments.mayar import (
    PAID_STATUSES,
    MayarError,
    get_payment_status,
    verify_webhook,
)
from core.payments.subscriptions import (
    activate_subscription,
    cancel_pending_subscription,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def webhook(request):
    logger.info(
        "mayar webhook hit: remote=%s ct=%s",
        request.META.get("REMOTE_ADDR"),
        request.content_type,
    )
    if not verify_webhook(request):
        logger.warning("mayar webhook: token verify failed")
        return Response(
            {"detail": "Invalid token."}, status=status.HTTP_401_UNAUTHORIZED
        )
    event = request.data.get("event") or ""
    data = request.data.get("data") or {}
    if not isinstance(data, dict):
        data = {}
    # v2: we store the payment-request id, which webhooks send as `productId`;
    # `id`/`transactionId` is the payment id (also what v1-era subs stored).
    refs = {str(data[k]) for k in ("productId", "transactionId", "id") if data.get(k)}
    logger.info(
        "mayar webhook payload: event=%r refs=%s data_keys=%s",
        event,
        sorted(refs),
        sorted(data.keys()),
    )
    if not refs:
        logger.warning("mayar webhook: missing payment ids; raw=%s", request.data)
        return Response(
            {"detail": "Missing transaction id."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    sub = Subscription.objects.filter(payment_ref__in=refs).first()
    if sub is None:
        logger.warning(
            "mayar webhook: subscription not found for refs=%s event=%s",
            sorted(refs),
            event,
        )
        return Response(
            {"detail": "Subscription not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if event in {"payment.received", "payment.success", "PAYMENT_RECEIVED"}:
        if sub.status == SubscriptionStatus.ACTIVE:
            logger.info("mayar webhook: sub=%s already ACTIVE, skip", sub.id)
            return Response({"ok": True})
        # The payload has no signature, so confirm with Mayar before granting.
        try:
            paid_status = get_payment_status(sub.payment_ref)["status"]
        except MayarError as exc:
            logger.warning(
                "mayar webhook: status re-fetch failed sub=%s: %s", sub.id, exc
            )
            return Response(
                {"detail": "Payment status check failed."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if paid_status not in PAID_STATUSES:
            logger.info(
                "mayar webhook: sub=%s Mayar status=%r, not paid yet; pollers will retry",
                sub.id,
                paid_status,
            )
            return Response({"ok": True})
        logger.info(
            "mayar webhook: activating subscription id=%s event=%s",
            sub.id,
            event,
        )
        try:
            activate_subscription(sub)
        except Exception:
            logger.exception(
                "mayar webhook: activate_subscription failed sub=%s", sub.id
            )
            return Response(
                {"detail": "Internal error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    elif event in {"payment.failed", "payment.expired"}:
        logger.info(
            "mayar webhook: cancelling pending subscription id=%s event=%s",
            sub.id,
            event,
        )
        try:
            cancel_pending_subscription(sub)
        except Exception:
            logger.exception(
                "mayar webhook: cancel_pending_subscription failed sub=%s",
                sub.id,
            )
            return Response(
                {"detail": "Internal error."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    else:
        logger.warning(
            "mayar webhook: unhandled event=%r for sub=%s status=%s",
            event,
            sub.id,
            sub.status,
        )

    return Response({"ok": True})
