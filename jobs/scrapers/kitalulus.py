"""HTML scraper for Kitalulus (kitalulus.com).

Two-phase: parse a listing URL for posting links, then fetch each detail page.

Detail pages carry a schema.org ``JobPosting`` JSON-LD block, so we read that
rather than the page's Tailwind markup — the publisher emits it specifically for
machine consumption by job aggregators, and it is far more stable than class
soup. Kitalulus serves it to an identifying bot User-Agent (verified 2026-09-09),
so no browser impersonation is involved.

Their robots.txt allows everything except ``/auth/`` and ``/my/``. Note it does
ban ``GPTBot`` outright — an anti-AI-training stance, not an anti-aggregator one.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from jobs.consts import BOT_USER_AGENT, JobType, RemoteOption
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kitalulus.com"
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 20.0
DEFAULT_SLEEP = 1.5
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3

JOB_LINK_RE = re.compile(r"^/lowongan/detail/([A-Za-z0-9\-]+)$")

# schema.org employmentType values → our JobType.
EMPLOYMENT_TO_JOBTYPE: dict[str, str] = {
    "FULL_TIME": JobType.FULL_TIME,
    "PART_TIME": JobType.PART_TIME,
    "CONTRACTOR": JobType.CONTRACT,
    "TEMPORARY": JobType.CONTRACT,
    "INTERN": JobType.INTERNSHIP,
}


def build_client() -> httpx.Client:
    """An honest, self-identifying client — nothing here is being circumvented."""
    return httpx.Client(
        headers={
            "User-Agent": BOT_USER_AGENT,
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

    Page 1 is the input URL unchanged. Kitalulus paginates client-side, so
    ``?page=N`` currently returns page 1 again; ``crawl`` dedupes across pages
    and stops once a page contributes nothing new.
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
        m = JOB_LINK_RE.match(a.get("href", ""))
        if not m:
            continue
        slug = m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        urls.append(urljoin(BASE_URL, f"/lowongan/detail/{slug}"))
    return urls


def _find_job_posting(html: str) -> dict | None:
    """Return the schema.org JobPosting object from a page's JSON-LD, if any."""
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw.strip())
        except (ValueError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            if item.get("@type") == "JobPosting":
                return item
            for node in item.get("@graph") or []:
                if isinstance(node, dict) and node.get("@type") == "JobPosting":
                    return node
    return None


def _html_to_text(*parts: str | None) -> str:
    html = "\n\n".join(p for p in parts if p)
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text("\n", strip=True)


def _location(posting: dict) -> str | None:
    job_location = posting.get("jobLocation")
    if isinstance(job_location, list):
        job_location = job_location[0] if job_location else None
    address = (job_location or {}).get("address") or {}
    parts = [address.get("addressLocality"), address.get("addressRegion")]
    return ", ".join(p for p in parts if p) or None


def _map_job_type(value) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return None
    job_type = EMPLOYMENT_TO_JOBTYPE.get(str(value).strip().upper())
    if job_type is None:
        logger.warning("unmapped employmentType: %r", value)
    return job_type


def _map_remote_option(posting: dict) -> str | None:
    # schema.org marks fully-remote roles with jobLocationType TELECOMMUTE.
    # Kitalulus emits no hybrid/on-site signal, so anything else stays unset
    # rather than being guessed at.
    if str(posting.get("jobLocationType") or "").strip().upper() == "TELECOMMUTE":
        return RemoteOption.REMOTE
    return None


def parse_detail(html: str, url: str) -> dict | None:
    """Parse a Kitalulus detail page into a Job-shaped dict.

    Returns ``None`` if the page carries no JobPosting JSON-LD, or that block
    lacks a title or description. Deliberately reads only the hiring
    organisation — no recruiter-identifying field is carried through.
    """
    posting = _find_job_posting(html)
    if posting is None:
        logger.warning("no JobPosting JSON-LD on detail page: %s", url)
        return None

    title = (posting.get("title") or "").strip()
    description = _html_to_text(posting.get("description"))
    if not title or not description:
        logger.warning("detail page missing title/description: %s", url)
        return None

    company = (posting.get("hiringOrganization") or {}).get("name")
    location = _location(posting)
    return {
        "url": url,
        "title": title[:255],
        "company": (company[:255] if company else None),
        "description": description,
        "location": (location[:255] if location else None),
        "job_type": _map_job_type(posting.get("employmentType")),
        "remote_option": _map_remote_option(posting),
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: httpx.Client | None = None,
) -> Iterator[dict]:
    """Yield parsed job posting dicts for the given Kitalulus listing URL.

    Stops early when a listing page returns no new postings or ``limit`` is hit.

    Example usage:
    https://www.kitalulus.com/lowongan/in-jakarta-selatan
    """
    owns_client = client is None
    client = client or build_client()
    yielded = 0
    seen: set[str] = set()
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
            fresh = [u for u in detail_urls if u not in seen]
            if not fresh:
                # Pagination is client-side: page N repeated page 1. Stop rather
                # than refetching the same postings.
                break
            seen.update(fresh)
            for detail_url in fresh:
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
