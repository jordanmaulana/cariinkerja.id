import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

PAID_STATUSES = {"paid", "success", "completed"}
FAILED_STATUSES = {"failed", "expired", "cancelled", "canceled"}


class MayarError(Exception):
    pass


def _base_url() -> str:
    return getattr(settings, "MAYAR_BASE_URL", "") or "https://api.mayar.id/hl/v1"


def _headers() -> dict:
    api_key = settings.MAYAR_API_KEY
    if not api_key:
        raise MayarError("MAYAR_API_KEY not configured.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_payment_link(
    *,
    name: str,
    amount: int,
    email: str,
    description: str,
    redirect_url: str,
    mobile: str = "",
) -> dict:
    payload = {
        "name": name,
        "amount": amount,
        "email": email,
        "description": description,
        "redirectUrl": redirect_url,
    }
    if mobile:
        payload["mobile"] = mobile

    try:
        resp = httpx.post(
            f"{_base_url()}/payment/create",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise MayarError(f"Mayar request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise MayarError(f"Mayar {resp.status_code}: {resp.text}")

    body = resp.json()
    data = body.get("data") or {}
    link = data.get("link")
    transaction_id = data.get("id") or data.get("transaction_id")
    if not link or not transaction_id:
        raise MayarError(f"Mayar response missing link/id: {body}")
    return {"link": link, "transaction_id": str(transaction_id)}


def get_payment_status(payment_id: str) -> dict:
    """GET /payment/{id}. Returns {"status": str, "raw": dict}."""
    if not payment_id:
        raise MayarError("payment_id is required.")
    try:
        resp = httpx.get(
            f"{_base_url()}/payment/{payment_id}",
            headers=_headers(),
            timeout=15,
        )
    except httpx.HTTPError as exc:
        raise MayarError(f"Mayar request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise MayarError(f"Mayar {resp.status_code}: {resp.text}")
    body = resp.json()
    data = body.get("data") or {}
    return {"status": str(data.get("status") or "").lower(), "raw": data}


def verify_webhook(request) -> bool:
    expected = getattr(settings, "MAYAR_WEBHOOK_TOKEN", "") or ""
    if not expected:
        logger.error("mayar webhook: MAYAR_WEBHOOK_TOKEN not configured")
        return False
    received = request.headers.get("X-Callback-Token") or request.headers.get(
        "x-callback-token"
    )
    if not received:
        logger.warning(
            "mayar webhook: missing X-Callback-Token header; headers=%s",
            list(request.headers.keys()),
        )
        return False
    if received != expected:
        logger.warning(
            "mayar webhook: token mismatch (received len=%d, expected len=%d)",
            len(received),
            len(expected),
        )
        return False
    return True
