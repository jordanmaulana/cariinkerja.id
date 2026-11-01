"""JSON-API scraper for Workable's job board (jobs.workable.com).

The stored crawl URL is Workable's human search page
(``https://jobs.workable.com/search?query=...&location=Indonesia``) so admins
can click it; ``crawl`` sends its ``query`` to the search API behind that page
(``/api/v1/jobs``), which returns 20 jobs per page with full descriptions and
pages via ``nextPageToken``. No key, no browser impersonation.

The API search is fuzzy ("developer" also hits "Business Development") and
returns old postings, so results are filtered here by title words and age.

Permission basis: robots.txt does not disallow ``/api/`` and the site signals
``Content-Signal: search=yes, ai-input=yes, ai-train=no``. The API itself is
undocumented. Job URLs stay unchanged (Workable's feed rule: candidate
attribution), so ``Job.url`` is the API ``url``.
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from jobs.consts import JobType, RemoteOption
from jobs.scrapers.dealls import _request_json
from jobs.scrapers.filters import is_blocked_company, title_has_words, title_words

logger = logging.getLogger(__name__)

API_URL = "https://jobs.workable.com/api/v1/jobs"
TIMEOUT = 20.0
DEFAULT_SLEEP = 1.5
USER_AGENT = "cariinkerja-bot/1.0 (+https://cariinkerja.id)"
# The search returns postings from years ago; ignore stale ones.
MAX_AGE_DAYS = 60

JOBTYPE_MAP: dict[str, str] = {
    "Full-time": JobType.FULL_TIME,
    "Part-time": JobType.PART_TIME,
    "Contract": JobType.CONTRACT,
    "Temporary": JobType.CONTRACT,
}

WORKPLACE_MAP: dict[str, str] = {
    "on_site": RemoteOption.ON_SITE,
    "hybrid": RemoteOption.HYBRID,
    "remote": RemoteOption.REMOTE,
}


def build_client() -> cffi_requests.Session:
    session = cffi_requests.Session(timeout=TIMEOUT)
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return session


def _created(job: dict) -> datetime | None:
    try:
        return datetime.fromisoformat(job["created"].replace("Z", "+00:00"))
    except (KeyError, AttributeError, ValueError):
        return None


def parse_job(job: dict) -> dict | None:
    """Map one API job to a Job-shaped dict; None if unusable."""
    url = job.get("url")
    title = (job.get("title") or "").strip()
    html = "".join(
        job.get(k) or ""
        for k in ("description", "requirementsSection", "benefitsSection")
    )
    description = BeautifulSoup(html, "lxml").get_text("\n", strip=True) if html else ""
    if not url or not title or not description:
        logger.warning("job missing url/title/description: id=%s", job.get("id"))
        return None
    company = (job.get("company") or {}).get("title") or None
    loc = job.get("location") or {}
    parts = (loc.get("city"), loc.get("subregion"), loc.get("countryName"))
    location = ", ".join(dict.fromkeys(p for p in parts if p)) or None
    return {
        "url": url,
        "title": title[:255],
        "company": company[:255] if company else None,
        "description": description,
        "location": location[:255] if location else None,
        "job_type": JOBTYPE_MAP.get(job.get("employmentType") or ""),
        "remote_option": WORKPLACE_MAP.get(job.get("workplace") or ""),
    }


def crawl(
    url: str,
    *,
    max_pages: int = 3,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield Indonesia jobs whose title has every word of the URL's ``query``.

    Always searches ``location=Indonesia`` (it includes remote jobs open to
    Indonesia), whatever the stored URL says. ``max_pages`` defaults to 3
    because the title filter drops much of each fuzzy 20-job page.

    Example usage:
    https://jobs.workable.com/search?query=backend+developer&location=Indonesia
    """
    query = dict(parse_qsl(urlparse(url).query)).get("query", "").strip()
    words = title_words(query)
    if not words:
        logger.warning("no query in workable crawl url: %s", url)
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    params = {"query": query, "location": "Indonesia"}
    owns_client = client is None
    client = client or build_client()
    seen: set[str] = set()
    yielded = 0
    try:
        for page in range(1, max_pages + 1):
            if page > 1:
                time.sleep(sleep + random.uniform(0, 0.3))
            try:
                payload = _request_json(client, f"{API_URL}?{urlencode(params)}")
            except Exception as exc:
                logger.error("listing fetch failed: page=%d — %s", page, exc)
                break
            for job in payload.get("jobs") or []:
                if limit is not None and yielded >= limit:
                    return
                if job.get("id") in seen:
                    continue
                seen.add(job.get("id"))
                created = _created(job)
                if created is None or created < cutoff:
                    continue
                if not title_has_words(job.get("title") or "", words):
                    continue
                parsed = parse_job(job)
                if parsed is None or is_blocked_company(parsed["company"]):
                    continue
                yielded += 1
                yield parsed
            token = payload.get("nextPageToken")
            if not token:
                break
            params["pageToken"] = token
    finally:
        if owns_client:
            client.close()
