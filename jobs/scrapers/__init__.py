from __future__ import annotations

from types import ModuleType
from urllib.parse import urlparse

from jobs.scrapers import dealls, indeed, jobstreet, linkedin
from profiles.consts import Source


def scraper_for_url(url: str) -> tuple[ModuleType | None, str | None]:
    """Resolve (scraper_module, source_value) for a crawl URL by hostname.

    Returns (None, None) for unknown or malformed URLs.
    """
    if not url:
        return (None, None)
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return (None, None)
    if not host:
        return (None, None)
    if host == "indeed.com" or host.endswith(".indeed.com"):
        return (indeed, Source.INDEED.value)
    if host == "jobstreet.com" or host.endswith(".jobstreet.com"):
        return (jobstreet, Source.JOBSTREET.value)
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        return (linkedin, Source.LINKEDIN.value)
    if host == "dealls.com" or host.endswith(".dealls.com"):
        return (dealls, Source.DEALLS.value)
    return (None, None)
