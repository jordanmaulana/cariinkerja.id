import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def send_discord_message(content: str) -> None:
    url = getattr(settings, "DISCORD_WEBHOOK_URL", "") or ""
    if not url:
        logger.info("discord webhook: DISCORD_WEBHOOK_URL not set; skip")
        return
    try:
        resp = httpx.post(url, json={"content": content}, timeout=10)
    except httpx.HTTPError as exc:
        logger.warning("discord webhook failed: %s", exc)
        return
    if resp.status_code >= 400:
        logger.warning("discord webhook %s: %s", resp.status_code, resp.text)
