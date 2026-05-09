import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from billing.models import Subscription
from core.payments.mayar import verify_webhook
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
    payment_ref = str(data.get("id") or data.get("transaction_id") or "")
    logger.info(
        "mayar webhook payload: event=%r payment_ref=%r data_keys=%s",
        event,
        payment_ref,
        sorted(data.keys()) if isinstance(data, dict) else None,
    )
    if not payment_ref:
        logger.warning("mayar webhook: missing payment_ref; raw=%s", request.data)
        return Response(
            {"detail": "Missing transaction id."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    sub = Subscription.objects.filter(payment_ref=payment_ref).first()
    if sub is None:
        logger.warning(
            "mayar webhook: subscription not found for payment_ref=%s event=%s",
            payment_ref,
            event,
        )
        return Response(
            {"detail": "Subscription not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if event in {"payment.received", "payment.success", "PAYMENT_RECEIVED"}:
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
