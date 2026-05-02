import json
import logging
from functools import lru_cache

import redis
from django.conf import settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _client() -> redis.Redis:
    url = getattr(settings, "REDIS_URL", None) or settings.CELERY_BROKER_URL
    return redis.Redis.from_url(url)


def publish(channel: str, payload: dict) -> None:
    try:
        _client().publish(channel, json.dumps(payload, default=str))
    except Exception:
        log.exception("realtime.publish failed channel=%s", channel)


def user_channel(user_id: int) -> str:
    return f"user:{user_id}:events"
