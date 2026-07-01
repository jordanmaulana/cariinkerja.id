"""JSON-API scraper for Dealls Indonesia (dealls.com, formerly SejutaCita).

Unlike the Indeed/Jobstreet/LinkedIn scrapers (which parse HTML), Dealls is a
Next.js SPA backed by a public, unauthenticated JSON API at ``api.sejutacita.id``.
Two-phase like the others: a listing call yields job slugs + pagination, then a
per-slug detail call carries the description.

The caller supplies a ``dealls.com`` listing URL verbatim (e.g.
``https://dealls.com/?location=remote&employment=partTime&employment=freelance``);
``_list_api_url`` translates its ``location`` / ``employment`` query params into the
API's ``workplaceTypes[i]`` / ``employmentTypes[i]`` params — the same mapping the
site's own JS performs.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from jobs.consts import JobType, RemoteOption
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

LIST_API = "https://api.sejutacita.id/v1/explore-job/job"
DETAIL_API = "https://api.sejutacita.id/v1/job-portal/job/slug/{slug}?guest=true"
JOB_URL = "https://dealls.com/loker/{slug}~{company_slug}"

ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 20.0
DEFAULT_SLEEP = 1.5
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
IMPERSONATE = "chrome131"
PAGE_LIMIT = 18

# Dealls employment type values → our JobType. Note: "freelance" has no direct
# JobType bucket and is mapped to PART_TIME by product decision.
EMPLOYMENT_TO_JOBTYPE: dict[str, str] = {
    "fullTime": JobType.FULL_TIME,
    "partTime": JobType.PART_TIME,
    "freelance": JobType.PART_TIME,
    "contract": JobType.CONTRACT,
    "internship": JobType.INTERNSHIP,
}

WORKPLACE_TO_REMOTE: dict[str, str] = {
    "remote": RemoteOption.REMOTE,
    "onSite": RemoteOption.ON_SITE,
    "hybrid": RemoteOption.HYBRID,
}


def build_client() -> cffi_requests.Session:
    session = cffi_requests.Session(impersonate=IMPERSONATE, timeout=TIMEOUT)
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": ACCEPT_LANGUAGE,
        }
    )
    return session


def _request_json(client: cffi_requests.Session, url: str) -> dict:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(url, allow_redirects=True)
            if resp.status_code in RETRY_STATUSES:
                raise RuntimeError(f"retryable status {resp.status_code}")
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


def _list_api_url(input_url: str, page: int) -> str:
    """Translate a dealls.com listing URL into a sejutacita list-API URL.

    ``?location=<v>`` values become ``workplaceTypes[i]`` and ``?employment=<v>``
    values become ``employmentTypes[i]`` — mirroring the site's own frontend.
    """
    employment: list[str] = []
    workplace: list[str] = []
    for key, value in parse_qsl(urlparse(input_url).query):
        if key == "employment":
            employment.append(value)
        elif key == "location":
            workplace.append(value)

    params: list[tuple[str, str]] = [
        ("page", str(page)),
        ("limit", str(PAGE_LIMIT)),
        ("published", "true"),
        ("status", "active"),
        ("sortParam", "mostRelevant"),
        ("sortBy", "asc"),
    ]
    for i, value in enumerate(employment):
        params.append((f"employmentTypes[{i}]", value))
    for i, value in enumerate(workplace):
        params.append((f"workplaceTypes[{i}]", value))
    return f"{LIST_API}?{urlencode(params)}"


def parse_listing(payload: dict) -> list[str]:
    """Return deduped job slugs from a list-API response payload."""
    docs = (payload.get("data") or {}).get("docs") or []
    seen: set[str] = set()
    slugs: list[str] = []
    for doc in docs:
        slug = doc.get("slug")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)
    return slugs


def _total_pages(payload: dict) -> int:
    return (payload.get("data") or {}).get("totalPages") or 1


def fetch_detail(client: cffi_requests.Session, slug: str) -> dict | None:
    """Fetch and return the ``data.result`` object for a job slug."""
    payload = _request_json(client, DETAIL_API.format(slug=slug))
    return (payload.get("data") or {}).get("result")


def _html_to_text(*parts: str | None) -> str:
    html = "\n\n".join(p for p in parts if p)
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text("\n", strip=True)


def _city_name(location: dict | None) -> str | None:
    if not location:
        return None
    city = location.get("city") or {}
    return city.get("name")


def parse_detail(result: dict) -> dict | None:
    """Parse a Dealls ``data.result`` object into a Job-shaped dict.

    Returns ``None`` if the record lacks a title or usable description.
    Deliberately ignores ``author`` (recruiter PII).
    """
    slug = result.get("slug")
    company = result.get("company") or {}
    company_slug = company.get("slug")
    if company_slug:
        url = JOB_URL.format(slug=slug, company_slug=company_slug)
    else:
        url = f"https://dealls.com/loker/{slug}"

    title = (result.get("role") or "").strip()
    description = _html_to_text(
        result.get("description"),
        result.get("responsibilities"),
        result.get("requirements"),
    )
    if not title or not description:
        logger.warning("detail missing title/description: slug=%s", slug)
        return None

    location = _city_name(result.get("location")) or _city_name(company.get("location"))

    employment_types = result.get("employmentTypes") or []
    job_type = None
    if employment_types:
        job_type = EMPLOYMENT_TO_JOBTYPE.get(employment_types[0])
        if job_type is None:
            logger.warning("unmapped employment type: %r", employment_types[0])

    workplace = result.get("workplaceType")
    remote_option = WORKPLACE_TO_REMOTE.get(workplace) if workplace else None
    if workplace and remote_option is None:
        logger.warning("unmapped workplaceType: %r", workplace)

    company_name = company.get("name")
    return {
        "url": url,
        "title": title[:255],
        "company": (company_name[:255] if company_name else None),
        "description": description,
        "location": (location[:255] if location else None),
        "job_type": job_type,
        "remote_option": remote_option,
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield parsed job posting dicts for the given Dealls listing URL.

    Stops early when a listing page returns no slugs, ``max_pages`` /
    ``totalPages`` is exhausted, or ``limit`` is hit.

    Example usage:
    https://dealls.com/?location=remote&employment=partTime&employment=freelance
    """
    owns_client = client is None
    client = client or build_client()
    yielded = 0
    try:
        for page in range(1, max_pages + 1):
            try:
                payload = _request_json(client, _list_api_url(url, page))
            except Exception as exc:
                logger.error("listing fetch failed: page=%d — %s", page, exc)
                break
            slugs = parse_listing(payload)
            if not slugs:
                break
            for slug in slugs:
                if limit is not None and yielded >= limit:
                    return
                time.sleep(sleep + random.uniform(0, 0.3))
                try:
                    result = fetch_detail(client, slug)
                except Exception as exc:
                    logger.error("detail fetch failed: slug=%s — %s", slug, exc)
                    continue
                if not result:
                    continue
                parsed = parse_detail(result)
                if parsed is None:
                    continue
                if is_blocked_company(parsed.get("company")):
                    continue
                yielded += 1
                yield parsed
            if page >= _total_pages(payload):
                break
            time.sleep(sleep + random.uniform(0, 0.3))
    finally:
        if owns_client:
            client.close()
