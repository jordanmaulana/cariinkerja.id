"""JSON-API scraper for Kalibrr Indonesia (kalibrr.com).

Kalibrr's own job board is served by a public, unauthenticated JSON API. Unlike
every other scraper here this one is **single-phase**: the search response
already carries the full description, company, location and tenure, so there is
no per-posting detail fetch. A whole crawl is one HTTP request.

The caller supplies a browsable Kalibrr search URL (e.g.
``https://www.kalibrr.com/job-board/te/software-engineer/co/Indonesia``);
``_list_api_url`` translates its ``/te/<keyword>`` and ``/co/<country>`` path
segments into the API's ``text`` / ``country`` params — the same mapping the
site's own JS performs.

Note ``text`` is the only keyword param the API honours: ``query``, ``q`` and
``keyword`` are silently ignored and return the unfiltered inventory, which
would look like a working crawl while quietly ignoring the Preference title.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Iterator
from urllib.parse import parse_qsl, unquote, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

from jobs.consts import BOT_USER_AGENT, JobType
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

LIST_API = "https://www.kalibrr.com/api/job_board/search"
JOB_URL = "https://www.kalibrr.com/c/{company_code}/jobs/{job_id}/{slug}"

ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 20.0
DEFAULT_SLEEP = 1.5
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
# API ceiling per request. Requests are sized down to `limit` when the caller
# gives one, so a production crawl (CRAWL_ITEM_LIMIT = 10) fetches ~55KB, not 550KB.
PAGE_LIMIT = 100
DEFAULT_COUNTRY = "Indonesia"

# Kalibrr `tenure` values → our JobType. Verified against the full Indonesian
# inventory (1086 postings, 2026-09-09): only these four occur. "Freelance" has
# no direct JobType bucket and is mapped to PART_TIME, matching the same
# product decision made for Dealls.
TENURE_TO_JOBTYPE: dict[str, str] = {
    "full time": JobType.FULL_TIME,
    "part time": JobType.PART_TIME,
    "freelance": JobType.PART_TIME,
    "contractual": JobType.CONTRACT,
    "internship": JobType.INTERNSHIP,
}


def build_client() -> httpx.Client:
    """An honest, self-identifying client.

    Kalibrr serves the full API response to this User-Agent (verified
    2026-09-09), so there is nothing here to impersonate or circumvent.
    """
    return httpx.Client(
        headers={
            "User-Agent": BOT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": ACCEPT_LANGUAGE,
        },
        follow_redirects=True,
        timeout=TIMEOUT,
    )


def _request_json(client: httpx.Client, url: str) -> dict:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(url)
            if resp.status_code in RETRY_STATUSES:
                raise httpx.HTTPStatusError(
                    f"retryable status {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_exc = exc
            backoff = (2**attempt) + random.uniform(0, 0.5)
            logger.warning(
                "GET %s failed (attempt %d/%d): %s — sleeping %.1fs",
                url,
                attempt + 1,
                MAX_RETRIES,
                exc,
                backoff,
            )
            time.sleep(backoff)
    assert last_exc is not None
    raise last_exc


def _path_segment(path: str, key: str) -> str | None:
    """Return the segment following ``/<key>/`` in a Kalibrr search path."""
    parts = [p for p in path.split("/") if p]
    for i, part in enumerate(parts):
        if part == key and i + 1 < len(parts):
            return unquote(parts[i + 1])
    return None


def _list_api_url(input_url: str, offset: int, page_size: int = PAGE_LIMIT) -> str:
    """Translate a kalibrr.com search URL into a job_board search-API URL.

    ``/te/<keyword>`` becomes ``text=<keyword>`` and ``/co/<country>`` becomes
    ``country=<country>``, mirroring the site's own frontend. An explicit
    ``?text=`` / ``?country=`` query param wins over the path form.
    """
    parsed = urlparse(input_url)
    query = dict(parse_qsl(parsed.query))

    keyword = query.get("text") or _path_segment(parsed.path, "te")
    country = (
        query.get("country") or _path_segment(parsed.path, "co") or DEFAULT_COUNTRY
    )

    params: list[tuple[str, str]] = [
        ("limit", str(page_size)),
        ("offset", str(offset)),
        ("country", country),
    ]
    if keyword:
        # Kalibrr slugs use hyphens; the API matches on plain text.
        params.append(("text", keyword.replace("-", " ")))
    return f"{LIST_API}?{urlencode(params)}"


def parse_listing(payload: dict) -> list[dict]:
    """Return deduped raw job objects from a search-API response payload."""
    seen: set[int] = set()
    jobs: list[dict] = []
    for job in payload.get("jobs") or []:
        job_id = job.get("id")
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        jobs.append(job)
    return jobs


def _total_count(payload: dict) -> int:
    return payload.get("count") or 0


def _html_to_text(*parts: str | None) -> str:
    html = "\n\n".join(p for p in parts if p)
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text("\n", strip=True)


def _location(job: dict) -> str | None:
    components = (job.get("google_location") or {}).get("address_components") or {}
    parts = [components.get("city"), components.get("region")]
    return ", ".join(p for p in parts if p) or None


def _map_job_type(tenure: str | None) -> str | None:
    if not tenure:
        return None
    job_type = TENURE_TO_JOBTYPE.get(tenure.strip().lower())
    if job_type is None:
        logger.warning("unmapped tenure: %r", tenure)
    return job_type


def parse_job(job: dict) -> dict | None:
    """Parse a Kalibrr search-result object into a Job-shaped dict.

    Returns ``None`` if the record lacks a title or usable description.
    Deliberately ignores ``es_recruiter_last_seen`` and every other
    recruiter-identifying field (PII).
    """
    job_id = job.get("id")
    company = job.get("company") or {}
    company_code = company.get("code")
    slug = job.get("slug")
    if not job_id or not company_code or not slug:
        logger.warning("job missing id/company code/slug: id=%s", job_id)
        return None

    title = (job.get("name") or "").strip()
    description = _html_to_text(job.get("description"), job.get("qualifications"))
    if not title or not description:
        logger.warning("job missing title/description: id=%s", job_id)
        return None

    company_name = company.get("name") or job.get("company_name")
    return {
        "url": JOB_URL.format(company_code=company_code, job_id=job_id, slug=slug),
        "title": title[:255],
        "company": (company_name[:255] if company_name else None),
        "description": description,
        "location": (_location(job) or "")[:255] or None,
        "job_type": _map_job_type(job.get("tenure")),
        # Kalibrr exposes only a boolean WFH flag — there is no hybrid/on-site
        # signal, so anything other than an explicit True stays unset rather
        # than being guessed at.
        "remote_option": None,
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: httpx.Client | None = None,
) -> Iterator[dict]:
    """Yield parsed job posting dicts for the given Kalibrr search URL.

    Single-phase: no per-posting detail requests are made. Stops early when a
    page returns no jobs, the reported ``count`` is exhausted, ``max_pages`` is
    reached, or ``limit`` is hit.

    Example usage:
    https://www.kalibrr.com/job-board/te/software-engineer/co/Indonesia
    """
    owns_client = client is None
    client = client or build_client()
    page_size = min(limit, PAGE_LIMIT) if limit else PAGE_LIMIT
    yielded = 0
    try:
        for page in range(max_pages):
            offset = page * page_size
            try:
                payload = _request_json(client, _list_api_url(url, offset, page_size))
            except Exception as exc:
                logger.error("listing fetch failed: offset=%d — %s", offset, exc)
                break
            jobs = parse_listing(payload)
            if not jobs:
                break
            for job in jobs:
                if limit is not None and yielded >= limit:
                    return
                parsed = parse_job(job)
                if parsed is None:
                    continue
                if is_blocked_company(parsed.get("company")):
                    continue
                yielded += 1
                yield parsed
            if offset + page_size >= _total_count(payload):
                break
            time.sleep(sleep + random.uniform(0, 0.3))
    finally:
        if owns_client:
            client.close()
