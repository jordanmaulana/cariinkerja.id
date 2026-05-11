from django.core.cache import cache
from django.utils import timezone

SHELL_PREFIX = "dashboard_stats_v3"
CHARTS_PREFIX = "dashboard_charts_v3"
TOP_PROFILES_PREFIX = "dashboard_top_profiles_v3"

SHELL_TTL = 300
CHARTS_TTL = 600
TOP_PROFILES_TTL = 600


def _today_key(prefix: str) -> str:
    return f"{prefix}:{timezone.localdate().isoformat()}"


def shell_key() -> str:
    return _today_key(SHELL_PREFIX)


def charts_key() -> str:
    return _today_key(CHARTS_PREFIX)


def top_profiles_key() -> str:
    return _today_key(TOP_PROFILES_PREFIX)


def bust_dashboard_cache() -> None:
    cache.delete_many([shell_key(), charts_key(), top_profiles_key()])
