import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

PAID_STATUSES = {"paid", "success", "completed"}
FAILED_STATUSES = {"failed", "expired", "cancelled", "canceled"}


class MayarError(Exception):
    pass


def _base_url() -> str:
    return getattr(settings, "MAYAR_BASE_URL", "") or "https://api.mayar.id/hl/v2"


def _headers() -> dict:
    api_key = settings.MAYAR_API_KEY
    if not api_key:
        raise MayarError("MAYAR_API_KEY not configured.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, **kwargs) -> dict:
    """Call Mayar v2 and return the `data` object.

    v2 can answer HTTP 200 with an error inside the body, so the body
    `statusCode` and `messages == "failed"` count as errors too.
    """
    try:
        resp = httpx.request(
            method, f"{_base_url()}{path}", headers=_headers(), timeout=15, **kwargs
        )
    except httpx.HTTPError as exc:
        raise MayarError(f"Mayar request failed: {exc}") from exc
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    code = int(body.get("statusCode") or resp.status_code)
    msg = body.get("messages") or body.get("message") or resp.text
    if resp.status_code >= 400 or code >= 400 or msg == "failed":
        raise MayarError(f"Mayar {code}: {msg}")
    return body.get("data") or {}


def create_payment_link(
    *,
    name: str,
    amount: int,
    email: str,
    description: str,
    redirect_url: str,
    mobile: str = "",
) -> dict:
    """POST /payments/create. Returns {"link": str, "payment_id": str}.

    `payment_id` is the payment-request id: the key for GET /payments/{id},
    sent as `productId` in webhooks.
    """
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
        data = _request("POST", "/payments/create", json=payload)
    except MayarError as exc:
        # v2 may reject redirectUrl with a 400. A 400 created nothing, so one
        # retry is safe. Never retry other errors: a 429 means "duplicate".
        if "redirectUrl" not in str(exc):
            raise
        logger.warning("mayar: redirectUrl rejected, retrying without it: %s", exc)
        payload.pop("redirectUrl")
        data = _request("POST", "/payments/create", json=payload)

    link = data.get("link")
    payment_id = data.get("id")
    if not link or not payment_id:
        raise MayarError(f"Mayar response missing link/id: {data}")
    return {"link": link, "payment_id": str(payment_id)}


def get_payment_status(payment_id: str) -> dict:
    """GET /payments/{id}. Returns {"status": str, "raw": dict}.

    v2 statuses: unpaid, paid, closed.
    """
    if not payment_id:
        raise MayarError("payment_id is required.")
    data = _request("GET", f"/payments/{payment_id}")
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
