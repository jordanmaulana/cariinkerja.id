"""JSON-API scraper for Himalayas (himalayas.app), a remote-only job board.

The crawl URL *is* the public search API
(``https://himalayas.app/jobs/api/search?q=...&employment_type=...``) — the
human site is Cloudflare-gated, the API is not. One call returns 20 jobs with
full descriptions, so unlike the other scrapers there is no detail fetch.

API terms (himalayas.app/terms#api): apply via ``applicationLink`` unchanged
(it points back to himalayas.app, which covers the link-back rule), and drop
expired jobs — expired ones are skipped here and ``expires_at`` is stored so
the SPA can label rows that expire later.
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from django.conf import settings

from jobs.consts import JobType, RemoteOption
from jobs.scrapers.dealls import _request_json
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

TIMEOUT = 20.0
DEFAULT_SLEEP = 1.5
IMPERSONATE = "chrome131"

EMPLOYMENT_TO_JOBTYPE: dict[str, str] = {
    "Full Time": JobType.FULL_TIME,
    "Part Time": JobType.PART_TIME,
    "Contractor": JobType.CONTRACT,
    "Temporary": JobType.CONTRACT,
    "Intern": JobType.INTERNSHIP,
}


def build_client() -> cffi_requests.Session:
    session = cffi_requests.Session(impersonate=IMPERSONATE, timeout=TIMEOUT)
    session.headers.update({"Accept": "application/json"})
    # Optional: without a key we share Himalayas' public allowance.
    key = getattr(settings, "HIMALAYAS_API_KEY", "")
    if key:
        session.headers["Authorization"] = f"Bearer {key}"
    return session


def _page_url(url: str, page: int) -> str:
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "page"]
    query.append(("page", str(page)))
    return urlunparse(parts._replace(query=urlencode(query)))


def _expires_at(job: dict) -> datetime | None:
    ts = job.get("expiryDate")
    return datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None


def parse_job(job: dict) -> dict | None:
    """Map one API job object to a Job-shaped dict; None if unusable."""
    url = job.get("applicationLink") or job.get("guid")
    title = (job.get("title") or "").strip()
    html = job.get("description") or job.get("excerpt") or ""
    description = BeautifulSoup(html, "lxml").get_text("\n", strip=True) if html else ""
    if not url or not title or not description:
        logger.warning("job missing url/title/description: guid=%s", job.get("guid"))
        return None

    employment = job.get("employmentType")
    company = job.get("companyName")
    # Indonesia first so the 255-char truncation below can't cut it off —
    # the relevance gate filters remote jobs whose list lacks Indonesia.
    countries = sorted(
        job.get("locationRestrictions") or [], key=lambda c: c != "Indonesia"
    )
    location = ", ".join(countries) or "Worldwide"
    return {
        "url": url,
        "title": title[:255],
        "company": company[:255] if company else None,
        "description": description,
        "location": location[:255],
        "job_type": EMPLOYMENT_TO_JOBTYPE.get(employment) if employment else None,
        "remote_option": RemoteOption.REMOTE,
        "expires_at": _expires_at(job),
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield parsed job dicts for a Himalayas search-API URL.

    Stops when a page is empty, ``max_pages`` is exhausted, or ``limit`` is
    hit. Already-expired jobs are skipped.

    Example usage:
    https://himalayas.app/jobs/api/search?q=flutter+developer&employment_type=Full+Time
    """
    owns_client = client is None
    client = client or build_client()
    seen: set[str] = set()
    yielded = 0
    now = datetime.now(timezone.utc)
    try:
        for page in range(1, max_pages + 1):
            if page > 1:
                time.sleep(sleep + random.uniform(0, 0.3))
            try:
                payload = _request_json(client, _page_url(url, page))
            except Exception as exc:
                logger.error("listing fetch failed: page=%d — %s", page, exc)
                break
            jobs = payload.get("jobs") or []
            if not jobs:
                break
            for job in jobs:
                if limit is not None and yielded >= limit:
                    return
                guid = job.get("guid")
                if guid in seen:
                    continue
                seen.add(guid)
                expires = _expires_at(job)
                if expires is not None and expires <= now:
                    continue
                parsed = parse_job(job)
                if parsed is None or is_blocked_company(parsed.get("company")):
                    continue
                yielded += 1
                yield parsed
    finally:
        if owns_client:
            client.close()
