"""HTML scraper for Jobstreet Indonesia (id.jobstreet.com).

Two-phase: parse a listing URL for posting links, then fetch each detail page.
The caller supplies the listing URL — any Jobstreet search/filter URL works.
"""

from __future__ import annotations

import logging
import random
import re
import time
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from jobs.consts import JobType, RemoteOption
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

BASE_URL = "https://id.jobstreet.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 15.0
DEFAULT_SLEEP = 1.5
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3

JOB_TYPE_FROM_LABEL: dict[str, str] = {
    "full time": JobType.FULL_TIME,
    "full-time": JobType.FULL_TIME,
    "penuh waktu": JobType.FULL_TIME,
    "part time": JobType.PART_TIME,
    "part-time": JobType.PART_TIME,
    "paruh waktu": JobType.PART_TIME,
    "contract": JobType.CONTRACT,
    "kontrak": JobType.CONTRACT,
    "casual/vacation": JobType.CONTRACT,
    "internship": JobType.INTERNSHIP,
    "magang": JobType.INTERNSHIP,
}

REMOTE_FROM_LABEL: dict[str, str] = {
    "remote": RemoteOption.REMOTE,
    "jarak jauh": RemoteOption.REMOTE,
    "bekerja jarak jauh": RemoteOption.REMOTE,
    "hybrid": RemoteOption.HYBRID,
    "hibrid": RemoteOption.HYBRID,
    "on-site": RemoteOption.ON_SITE,
    "on site": RemoteOption.ON_SITE,
    "di kantor": RemoteOption.ON_SITE,
}

JOB_LINK_RE = re.compile(r"^/(?:id/)?job/(\d+)")


def build_client() -> httpx.Client:
    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": ACCEPT_LANGUAGE,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
        },
        follow_redirects=True,
        timeout=TIMEOUT,
    )


def _request(client: httpx.Client, url: str) -> str:
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
            return resp.text
        except (httpx.HTTPError,) as exc:
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


def iter_listing_pages(url: str, max_pages: int) -> Iterator[str]:
    """Yield up to ``max_pages`` paginated URLs derived from ``url``.

    Page 1 is the input URL unchanged. Subsequent pages set/replace the
    ``page`` query param.
    """
    parsed = urlparse(url)
    base_query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "page"]
    for page in range(1, max_pages + 1):
        if page == 1:
            yield url
            continue
        query = urlencode(base_query + [("page", str(page))])
        yield urlunparse(parsed._replace(query=query))


def parse_listing(html: str) -> list[str]:
    """Return absolute, deduped detail URLs from a listing page."""
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    urls: list[str] = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        m = JOB_LINK_RE.match(href)
        if not m:
            continue
        job_id = m.group(1)
        if job_id in seen:
            continue
        seen.add(job_id)
        canonical = f"/id/job/{job_id}?type=standard&ref=search-standalone"
        urls.append(urljoin(BASE_URL, canonical))
    return urls


def _map_job_type(text: str | None) -> str | None:
    if not text:
        return None
    key = text.strip().lower()
    if key in JOB_TYPE_FROM_LABEL:
        return JOB_TYPE_FROM_LABEL[key]
    logger.warning("unmapped job_type label: %r", text)
    return None


def _map_remote_option(location_text: str, page_text: str) -> str | None:
    """Detect work arrangement from location string and full page text.

    Jobstreet ID encodes remote/hybrid as a parenthetical suffix on the
    location (e.g. ``"Jakarta Barat, Jakarta Raya (Jarak jauh)"``). On-site
    postings have no suffix.
    """
    haystack = f"{location_text}\n{page_text}".lower()
    paren = re.search(r"\(([^)]+)\)\s*$", location_text.strip())
    if paren:
        label = paren.group(1).strip().lower()
        if label in REMOTE_FROM_LABEL:
            return REMOTE_FROM_LABEL[label]
        logger.warning("unmapped remote label in location parens: %r", label)
    for label, value in REMOTE_FROM_LABEL.items():
        if label in haystack:
            return value
    return None


def _strip_remote_suffix(location_text: str) -> str:
    return re.sub(r"\s*\([^)]+\)\s*$", "", location_text).strip()


def parse_detail(html: str, url: str) -> dict | None:
    """Parse a Jobstreet detail page into a Job-shaped dict.

    Returns ``None`` if the page does not look like a job detail page
    (missing title or description).
    """
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one('[data-automation="job-detail-title"]')
    desc_el = soup.select_one('[data-automation="jobAdDetails"]')
    if not title_el or not desc_el:
        logger.warning("detail page missing title/description: %s", url)
        return None
    location_el = soup.select_one('[data-automation="job-detail-location"]')
    worktype_el = soup.select_one('[data-automation="job-detail-work-type"]')
    company_el = soup.select_one('[data-automation="advertiser-name"]')
    location_raw = location_el.get_text(" ", strip=True) if location_el else ""
    company = company_el.get_text(" ", strip=True) if company_el else None

    return {
        "url": url,
        "title": title_el.get_text(" ", strip=True)[:255],
        "company": (company[:255] if company else None),
        "description": desc_el.get_text("\n", strip=True),
        "location": _strip_remote_suffix(location_raw)[:255] or None,
        "job_type": _map_job_type(
            worktype_el.get_text(" ", strip=True) if worktype_el else None
        ),
        "remote_option": _map_remote_option(location_raw, soup.get_text(" ")),
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: httpx.Client | None = None,
) -> Iterator[dict]:
    """Yield parsed job posting dicts for the given Jobstreet listing URL.

    Stops early when a listing page returns no postings or ``limit`` is hit.

    Example usage:
    https://id.jobstreet.com/mobile-developer-jobs
    """
    owns_client = client is None
    client = client or build_client()
    yielded = 0
    try:
        for listing_url in iter_listing_pages(url, max_pages):
            try:
                listing_html = _request(client, listing_url)
            except httpx.HTTPError as exc:
                logger.error("listing fetch failed: %s — %s", listing_url, exc)
                break
            detail_urls = parse_listing(listing_html)
            if not detail_urls:
                logger.warning(
                    "no detail links parsed from listing %s "
                    "(possible soft block or markup change)",
                    listing_url,
                )
                break
            for detail_url in detail_urls:
                if limit is not None and yielded >= limit:
                    return
                time.sleep(sleep + random.uniform(0, 0.3))
                try:
                    detail_html = _request(client, detail_url)
                except httpx.HTTPError as exc:
                    logger.error("detail fetch failed: %s — %s", detail_url, exc)
                    continue
                parsed = parse_detail(detail_html, detail_url)
                if parsed is None:
                    continue
                if is_blocked_company(parsed.get("company")):
                    continue
                yielded += 1
                yield parsed
            time.sleep(sleep + random.uniform(0, 0.3))
    finally:
        if owns_client:
            client.close()
