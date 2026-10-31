"""JSON-API scraper for Jobicy (jobicy.com), a remote-only job board.

The crawl URL *is* the free public API
(``https://jobicy.com/api/jobs?geo=apac&tag=...&count=20``). One call returns
full descriptions, so there is no detail fetch. The feed only covers the last
7 days, newest first, paged by an opaque ``nextCursor``.

API terms (jobicy.com/jobs-rss-feed): credit Jobicy with a direct link to the
source (the SPA shows "via Jobicy"), and apply buttons must go to the job
``url`` from the feed — on the free API that is the jobicy.com job page, kept
unchanged as ``Job.url``. Start a sync pass no more than once per hour.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from jobs.consts import JobType, RemoteOption
from jobs.scrapers.dealls import _request_json, build_client
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

DEFAULT_SLEEP = 1.5

JOBTYPE_MAP: dict[str, str] = {
    "Full-Time": JobType.FULL_TIME,
    "Part-Time": JobType.PART_TIME,
    "Contract": JobType.CONTRACT,
    "Internship": JobType.INTERNSHIP,
}


def _cursor_url(url: str, cursor: str) -> str:
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "cursor"]
    query.append(("cursor", cursor))
    return urlunparse(parts._replace(query=urlencode(query)))


def parse_job(job: dict) -> dict | None:
    """Map one API job object to a Job-shaped dict; None if unusable."""
    url = job.get("url")
    title = (job.get("jobTitle") or "").strip()
    html = job.get("jobDescription") or job.get("jobExcerpt") or ""
    description = BeautifulSoup(html, "lxml").get_text("\n", strip=True) if html else ""
    if not url or not title or not description:
        logger.warning("job missing url/title/description: id=%s", job.get("id"))
        return None

    company = job.get("companyName")
    # jobGeo comes as e.g. "Canada,  USA" — normalise the spacing.
    geo = [p.strip() for p in (job.get("jobGeo") or "").split(",") if p.strip()]
    job_type = next(
        (JOBTYPE_MAP[t] for t in job.get("jobType") or [] if t in JOBTYPE_MAP), None
    )
    return {
        "url": url,
        "title": title[:255],
        "company": company[:255] if company else None,
        "description": description,
        "location": (", ".join(geo) or "Anywhere")[:255],
        "job_type": job_type,
        "remote_option": RemoteOption.REMOTE,
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield parsed job dicts for a Jobicy API URL.

    Stops when the feed has no more pages, ``max_pages`` is exhausted, or
    ``limit`` is hit.

    Example usage:
    https://jobicy.com/api/jobs?geo=apac&tag=flutter+developer&count=20
    """
    # ponytail: one request per preference per crawl pass. Fine while the beat
    # runs >= 1h apart (Jobicy's sync-pass limit); switch to one shared hourly
    # feed fetch + local title filtering if preferences grow into the hundreds.
    owns_client = client is None
    client = client or build_client()
    seen: set = set()
    yielded = 0
    page_url = url
    try:
        for page in range(1, max_pages + 1):
            if page > 1:
                time.sleep(sleep + random.uniform(0, 0.3))
            try:
                payload = _request_json(client, page_url)
            except Exception as exc:
                logger.error("listing fetch failed: page=%d — %s", page, exc)
                break
            for job in payload.get("jobs") or []:
                if limit is not None and yielded >= limit:
                    return
                if job.get("id") in seen:
                    continue
                seen.add(job.get("id"))
                parsed = parse_job(job)
                if parsed is None or is_blocked_company(parsed.get("company")):
                    continue
                yielded += 1
                yield parsed
            cursor = payload.get("nextCursor")
            if not payload.get("hasMore") or not cursor:
                break
            page_url = _cursor_url(url, cursor)
    finally:
        if owns_client:
            client.close()
