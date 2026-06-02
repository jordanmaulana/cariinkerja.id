"""HTML scraper for Glints Indonesia (glints.com/id).

Two-phase: parse a listing URL for posting links, then fetch each detail page.
The caller supplies the listing URL — any Glints ``/explore`` search URL works.

Glints is a Next.js app behind a custom WAF ("Glints - Firewall", HTTP 403 to
plain clients). We pass it with ``curl_cffi`` Chrome TLS impersonation (same
technique as ``indeed.py``). Job data is read from the embedded
``<script id="__NEXT_DATA__">`` JSON, not the DOM:

- Listing page: ``props.pageProps.initialJobs.jobsInPage`` (page 1, ~30 jobs).
- Detail page:  ``props.pageProps.initialData.data`` (full job incl. description).

Pagination cap: only page 1 is server-rendered. Deeper pages load client-side
via ``POST /api/v2/graphql`` which requires a logged-in session
(``NO_PERMISSION`` when unauthenticated), so an unauthenticated crawl yields at
most the ~30 page-1 jobs. ``max_pages`` is accepted for signature parity but
anything past page 1 is skipped (logged, not silent).
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any, Iterator

from curl_cffi import requests as cffi_requests

from jobs.consts import JobType, RemoteOption

logger = logging.getLogger(__name__)

BASE_URL = "https://glints.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 25.0
DEFAULT_SLEEP = 2.0
RETRY_STATUSES = {403, 429, 500, 502, 503, 504}
MAX_RETRIES = 3
IMPERSONATE = "chrome131"

FIREWALL_MARKERS: tuple[str, ...] = ("glints - firewall",)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
# /id/opportunities/jobs/<slug>/<uuid>
DETAIL_RE = re.compile(
    r"/id/opportunities/jobs/([a-z0-9\-]+)/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
)

# Glints job ``type`` -> our JobType. DAILY / unknown fall through to None.
GLINTS_JT: dict[str, str] = {
    "FULL_TIME": JobType.FULL_TIME,
    "PART_TIME": JobType.PART_TIME,
    "CONTRACT": JobType.CONTRACT,
    "INTERNSHIP": JobType.INTERNSHIP,
    "PROJECT_BASED": JobType.CONTRACT,
    "FREELANCE": JobType.CONTRACT,
}

GLINTS_RO: dict[str, str] = {
    "REMOTE": RemoteOption.REMOTE,
    "ONSITE": RemoteOption.ON_SITE,
    "HYBRID": RemoteOption.HYBRID,
}


class GlintsFirewall(RuntimeError):
    """Glints served its WAF interstitial instead of content."""


def build_client() -> cffi_requests.Session:
    session = cffi_requests.Session(impersonate=IMPERSONATE, timeout=TIMEOUT)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": ACCEPT_LANGUAGE,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
        }
    )
    return session


def _detect_firewall(html: str) -> str | None:
    m = TITLE_RE.search(html)
    if not m:
        return None
    title = m.group(1).strip().lower()
    for marker in FIREWALL_MARKERS:
        if marker in title:
            return marker
    return None


def _request(client: cffi_requests.Session, url: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(url, allow_redirects=True)
            if resp.status_code in RETRY_STATUSES:
                raise RuntimeError(f"retryable status {resp.status_code}")
            resp.raise_for_status()
            text = resp.text
            marker = _detect_firewall(text)
            if marker:
                raise GlintsFirewall(
                    f"Glints firewall detected on {url} (marker={marker!r})"
                )
            return text
        except GlintsFirewall:
            raise
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


def _next_data(html: str) -> dict | None:
    m = NEXT_DATA_RE.search(html)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def iter_listing_pages(url: str, max_pages: int) -> Iterator[str]:
    """Yield listing page URLs.

    Only page 1 is server-rendered (the rest load via an authed GraphQL call),
    so we always yield just the input URL. ``max_pages > 1`` is logged so the
    cap isn't silent.
    """
    if max_pages > 1:
        logger.info(
            "glints: max_pages=%d requested but only page 1 is reachable "
            "without auth — crawling page 1 only",
            max_pages,
        )
    yield url


def parse_listing(html: str) -> list[str]:
    """Return absolute, deduped detail URLs from a listing page.

    Glints renders each job card as a link
    ``/id/opportunities/jobs/<slug>/<uuid>``; a regex sweep over the markup
    beats walking an 800KB+ DOM. Deduped by uuid, order preserved.
    """
    seen: dict[str, str] = {}
    for slug, uuid in DETAIL_RE.findall(html):
        if uuid not in seen:
            seen[uuid] = f"{BASE_URL}/id/opportunities/jobs/{slug}/{uuid}"
    return list(seen.values())


def _draftjs_to_text(raw: Any) -> str | None:
    """Decode a Draft.js raw content-state string to plain text."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    blocks = data.get("blocks")
    if not isinstance(blocks, list):
        return None
    text = "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict)).strip()
    return text or None


def parse_detail(html: str, url: str) -> dict | None:
    """Parse a Glints detail page into a Job-shaped dict.

    Returns ``None`` if title or description cannot be recovered.
    """
    data = _next_data(html)
    d = None
    if data:
        d = (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialData", {})
            .get("data")
        )
    if not isinstance(d, dict):
        logger.warning("glints detail page missing __NEXT_DATA__ job: %s", url)
        return None

    raw_title = d.get("title")
    title = raw_title.strip() if isinstance(raw_title, str) else None

    description = _draftjs_to_text(d.get("descriptionJsonString"))

    if not title or not description:
        logger.warning("glints detail page missing title/description: %s", url)
        return None

    company = None
    org = d.get("company")
    if isinstance(org, dict):
        name = org.get("name")
        if isinstance(name, str) and name.strip():
            company = name.strip()

    location = None
    loc = d.get("location")
    if isinstance(loc, dict):
        loc_name = loc.get("formattedName") or loc.get("name")
        if isinstance(loc_name, str) and loc_name.strip():
            location = loc_name.strip()

    job_type = None
    raw_type = d.get("type")
    if isinstance(raw_type, str):
        job_type = GLINTS_JT.get(raw_type.strip().upper())
        if job_type is None:
            logger.info("glints: unmapped job type %r", raw_type)

    remote_option = None
    raw_arrangement = d.get("workArrangementOption")
    if isinstance(raw_arrangement, str):
        remote_option = GLINTS_RO.get(raw_arrangement.strip().upper())

    return {
        "url": url,
        "title": title[:255],
        "company": (company[:255] if company else None),
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
    """Yield parsed job posting dicts for the given Glints listing URL.

    Stops early when the listing returns no postings, ``limit`` is hit, or the
    Glints firewall blocks a request (retrying without a fingerprint change
    won't help — abort and surface clearly).

    Example usage:
    https://glints.com/id/opportunities/jobs/explore?keyword=software+engineer&country=ID
    """
    owns_client = client is None
    client = client or build_client()
    yielded = 0
    try:
        for listing_url in iter_listing_pages(url, max_pages):
            try:
                listing_html = _request(client, listing_url)
            except GlintsFirewall as exc:
                logger.error(
                    "firewall hit on listing %s — aborting: %s", listing_url, exc
                )
                break
            except Exception as exc:
                logger.error("listing fetch failed: %s — %s", listing_url, exc)
                break
            detail_urls = parse_listing(listing_html)
            if not detail_urls:
                break
            for detail_url in detail_urls:
                if limit is not None and yielded >= limit:
                    return
                time.sleep(sleep + random.uniform(0, 0.3))
                try:
                    detail_html = _request(client, detail_url)
                except GlintsFirewall as exc:
                    logger.error(
                        "firewall hit on detail %s — aborting: %s", detail_url, exc
                    )
                    return
                except Exception as exc:
                    logger.error("detail fetch failed: %s — %s", detail_url, exc)
                    continue
                parsed = parse_detail(detail_html, detail_url)
                if parsed is None:
                    continue
                yielded += 1
                yield parsed
    finally:
        if owns_client:
            client.close()
