"""HTML scraper for Indeed Indonesia (id.indeed.com).

Two-phase: parse a listing URL for posting links, then fetch each detail page.
The caller supplies the listing URL — any Indeed search/filter URL works.

Indeed gates traffic with Cloudflare; uses ``curl_cffi`` with Chrome TLS
impersonation to pass the JA3/HTTP2 fingerprint check. If Cloudflare escalates
to an interactive challenge (Turnstile/hCaptcha), this module will raise
``CloudflareChallenge`` — at that point the next step is Playwright + stealth.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from jobs.consts import JobType, RemoteOption

logger = logging.getLogger(__name__)

BASE_URL = "https://id.indeed.com"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) "
    "Gecko/20100101 Firefox/133.0"
)
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 20.0
DEFAULT_SLEEP = 2.5
RETRY_STATUSES = {403, 429, 500, 502, 503, 504}
MAX_RETRIES = 3
IMPERSONATE = "firefox133"

CF_TITLE_MARKERS: tuple[str, ...] = (
    "additional verification required",
    "just a moment",
    "security check",
    "attention required",
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

EMPLOYMENT_TYPE_MAP: dict[str, str] = {
    "FULL_TIME": JobType.FULL_TIME,
    "FULLTIME": JobType.FULL_TIME,
    "PART_TIME": JobType.PART_TIME,
    "PARTTIME": JobType.PART_TIME,
    "CONTRACTOR": JobType.CONTRACT,
    "CONTRACT": JobType.CONTRACT,
    "TEMPORARY": JobType.CONTRACT,
    "INTERN": JobType.INTERNSHIP,
    "INTERNSHIP": JobType.INTERNSHIP,
}

LOCATION_TYPE_MAP: dict[str, str] = {
    "TELECOMMUTE": RemoteOption.REMOTE,
}

REMOTE_HINT_MAP: dict[str, str] = {
    "remote": RemoteOption.REMOTE,
    "jarak jauh": RemoteOption.REMOTE,
    "bekerja jarak jauh": RemoteOption.REMOTE,
    "wfh": RemoteOption.REMOTE,
    "work from home": RemoteOption.REMOTE,
    "hybrid": RemoteOption.HYBRID,
    "hibrid": RemoteOption.HYBRID,
    "on-site": RemoteOption.ON_SITE,
    "on site": RemoteOption.ON_SITE,
    "di kantor": RemoteOption.ON_SITE,
    "wfo": RemoteOption.ON_SITE,
}

DATA_JK_RE = re.compile(r"""data-jk=["']([^"']+)["']""")


class CloudflareChallenge(RuntimeError):
    """Indeed served a Cloudflare interstitial instead of content."""


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


def _detect_cloudflare(html: str) -> str | None:
    """Return marker name if response looks like a CF/Indeed gate page.

    Only inspects the <title>. Substring scans over the whole body produce
    false positives because Indeed embeds CF JS asset URLs (e.g.
    ``challenge-platform``) into normal listing pages.
    """
    m = TITLE_RE.search(html)
    if not m:
        return None
    title = m.group(1).strip().lower()
    for marker in CF_TITLE_MARKERS:
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
            marker = _detect_cloudflare(text)
            if marker:
                raise CloudflareChallenge(
                    f"Cloudflare interstitial detected on {url} (marker={marker!r})"
                )
            return text
        except CloudflareChallenge:
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


def iter_listing_pages(url: str, max_pages: int) -> Iterator[str]:
    """Yield up to ``max_pages`` paginated URLs derived from ``url``.

    Page 1 is the input URL unchanged. Subsequent pages set/replace the
    ``start`` query param in steps of 10 (Indeed's pagination convention).
    """
    parsed = urlparse(url)
    base_query = [(k, v) for k, v in parse_qsl(parsed.query) if k != "start"]
    for page_idx in range(max_pages):
        if page_idx == 0:
            yield url
            continue
        query = urlencode(base_query + [("start", str(page_idx * 10))])
        yield urlunparse(parsed._replace(query=query))


def parse_listing(html: str) -> list[str]:
    """Return absolute, deduped detail URLs from a listing page.

    Indeed's listing markup tags every job card with ``data-jk="<id>"``;
    a regex sweep beats parsing a 1MB+ DOM with bs4. Order preserved,
    duplicates dropped.
    """
    seen: dict[str, None] = {}
    for jk in DATA_JK_RE.findall(html):
        jk = jk.strip()
        if jk and jk not in seen:
            seen[jk] = None
    return [f"{BASE_URL}/viewjob?jk={jk}&from=serp&vjs=3" for jk in seen]


def _extract_jsonld_jobposting(soup: BeautifulSoup) -> dict | None:
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates: list[Any] = []
        if isinstance(data, list):
            candidates.extend(data)
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                candidates.extend(data["@graph"])
            else:
                candidates.append(data)
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return None


def _map_employment_type(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        if not value:
            return None
        value = value[0]
    if not isinstance(value, str):
        return None
    key = value.strip().upper().replace("-", "_").replace(" ", "_")
    if key in EMPLOYMENT_TYPE_MAP:
        return EMPLOYMENT_TYPE_MAP[key]
    logger.warning("unmapped employmentType: %r", value)
    return None


def _map_remote_option(jsonld: dict | None, title: str, description: str) -> str | None:
    if jsonld:
        loc_type = jsonld.get("jobLocationType")
        if isinstance(loc_type, str):
            mapped = LOCATION_TYPE_MAP.get(loc_type.strip().upper())
            if mapped:
                return mapped
    haystack = f"{title}\n{description}".lower()
    for label, value in REMOTE_HINT_MAP.items():
        if label in haystack:
            return value
    return None


def _location_from_jsonld(jsonld: dict) -> str | None:
    loc = jsonld.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else None
    if not isinstance(loc, dict):
        return None
    addr = loc.get("address")
    if not isinstance(addr, dict):
        return None
    parts = [
        addr.get("addressLocality"),
        addr.get("addressRegion"),
    ]
    joined = ", ".join(p for p in parts if isinstance(p, str) and p.strip())
    if joined:
        return joined
    country = addr.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    if isinstance(country, str) and country.strip():
        return country.strip()
    return None


def parse_detail(html: str, url: str) -> dict | None:
    """Parse an Indeed detail page into a Job-shaped dict.

    Returns ``None`` if title or description cannot be recovered.
    """
    soup = BeautifulSoup(html, "lxml")
    jsonld = _extract_jsonld_jobposting(soup)

    title: str | None = None
    description: str | None = None
    location: str | None = None
    job_type: str | None = None

    if jsonld:
        raw_title = jsonld.get("title")
        if isinstance(raw_title, str):
            title = raw_title.strip()
        raw_desc = jsonld.get("description")
        if isinstance(raw_desc, str):
            description = BeautifulSoup(raw_desc, "lxml").get_text("\n", strip=True)
        location = _location_from_jsonld(jsonld)
        job_type = _map_employment_type(jsonld.get("employmentType"))

    if not title:
        title_el = soup.select_one(
            'h1.jobsearch-JobInfoHeader-title, [data-testid="jobsearch-JobInfoHeader-title"]'
        )
        if title_el:
            title = title_el.get_text(" ", strip=True)
    if not description:
        desc_el = soup.select_one("#jobDescriptionText")
        if desc_el:
            description = desc_el.get_text("\n", strip=True)
    if not location:
        loc_el = soup.select_one(
            '[data-testid="inlineHeader-companyLocation"], [data-testid="job-location"]'
        )
        if loc_el:
            location = loc_el.get_text(" ", strip=True)

    if not title or not description:
        logger.warning("detail page missing title/description: %s", url)
        return None

    remote_option = _map_remote_option(jsonld, title, description)

    return {
        "url": url,
        "title": title[:255],
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
    """Yield parsed job posting dicts for the given Indeed listing URL.

    Stops early when a listing page returns no postings, ``limit`` is hit,
    or a Cloudflare interstitial is detected (retrying without a fingerprint
    change won't help — abort and surface clearly).
    """
    owns_client = client is None
    client = client or build_client()
    yielded = 0
    try:
        for listing_url in iter_listing_pages(url, max_pages):
            try:
                listing_html = _request(client, listing_url)
            except CloudflareChallenge as exc:
                logger.error(
                    "CF gate hit on listing %s — aborting: %s", listing_url, exc
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
                except CloudflareChallenge as exc:
                    logger.error(
                        "CF gate hit on detail %s — aborting: %s", detail_url, exc
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
            time.sleep(sleep + random.uniform(0, 0.3))
    finally:
        if owns_client:
            client.close()
