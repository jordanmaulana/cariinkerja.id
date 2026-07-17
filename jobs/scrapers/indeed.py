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
from jobs.scrapers.filters import is_blocked_company

logger = logging.getLogger(__name__)

BASE_URL = "https://id.indeed.com"
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 20.0
DEFAULT_SLEEP = 2.5
RETRY_STATUSES = {403, 429, 500, 502, 503, 504}
MAX_RETRIES = 3
# Detail pages are CF-gated harder than the SERP. A single gated detail must
# not kill the crawl; abort only after this many *consecutive* gated details
# (fingerprint rotation already exhausted on each) — the session/IP is burned.
CF_ABORT_THRESHOLD = 3
# Cloudflare fingerprints go stale; rotate on a CF block. Keep current-ish.
# `crawl` tries these in order and keeps the first that isn't gated.
IMPERSONATE_TARGETS: tuple[str, ...] = ("firefox147", "chrome146", "safari184")

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


def build_client(target: str = IMPERSONATE_TARGETS[0]) -> cffi_requests.Session:
    # No manual User-Agent: curl_cffi sets one matching ``target`` so the UA
    # and TLS fingerprint stay consistent (a Firefox UA on a Chrome
    # fingerprint is itself a bot signal).
    session = cffi_requests.Session(impersonate=target, timeout=TIMEOUT)
    session.headers.update(
        {
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


def _request(
    client: cffi_requests.Session,
    url: str,
    headers: dict[str, str] | None = None,
) -> str:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(url, allow_redirects=True, headers=headers)
            text = resp.text
            # Detect the CF gate FIRST: it often rides on a 403, and retrying
            # the same fingerprint won't clear it — surface it so the caller
            # rotates fingerprints instead of burning MAX_RETRIES.
            marker = _detect_cloudflare(text)
            if marker:
                raise CloudflareChallenge(
                    f"Cloudflare interstitial detected on {url} "
                    f"(marker={marker!r}, status={resp.status_code})"
                )
            if resp.status_code in RETRY_STATUSES:
                raise RuntimeError(f"retryable status {resp.status_code}")
            resp.raise_for_status()
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
    company: str | None = None

    if jsonld:
        raw_title = jsonld.get("title")
        if isinstance(raw_title, str):
            title = raw_title.strip()
        raw_desc = jsonld.get("description")
        if isinstance(raw_desc, str):
            description = BeautifulSoup(raw_desc, "lxml").get_text("\n", strip=True)
        location = _location_from_jsonld(jsonld)
        job_type = _map_employment_type(jsonld.get("employmentType"))
        org = jsonld.get("hiringOrganization")
        if isinstance(org, dict):
            org_name = org.get("name")
            if isinstance(org_name, str) and org_name.strip():
                company = org_name.strip()

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
    if not company:
        company_el = soup.select_one('[data-testid="inlineHeader-companyName"]')
        if company_el:
            company = company_el.get_text(" ", strip=True)

    if not title or not description:
        logger.warning("detail page missing title/description: %s", url)
        return None

    remote_option = _map_remote_option(jsonld, title, description)

    return {
        "url": url,
        "title": title[:255],
        "company": (company[:255] if company else None),
        "description": description,
        "location": (location[:255] if location else None),
        "job_type": job_type,
        "remote_option": remote_option,
    }


def _warm_up(client: cffi_requests.Session) -> None:
    """Best-effort homepage GET to seed Cloudflare clearance cookies.

    Mimics a real session entering via the homepage before the SERP. Failures
    are swallowed — warm-up must never abort fingerprint selection.
    """
    try:
        client.get(BASE_URL, allow_redirects=True)
    except Exception as exc:
        logger.debug("warm-up GET failed (non-fatal): %s", exc)


def _open_working_client(first_url: str) -> tuple[cffi_requests.Session, str, str]:
    """Open a client with the first fingerprint that isn't Cloudflare-gated.

    Reuses the real page-1 fetch as the probe (no extra request beyond a light
    homepage warm-up). Rotates through ``IMPERSONATE_TARGETS`` on any fetch
    failure and re-raises the last error if every fingerprint is blocked.
    Returns ``(client, target, html)`` so the detail loop knows which
    fingerprint won and where to resume rotating.
    """
    last_exc: Exception | None = None
    for target in IMPERSONATE_TARGETS:
        client = build_client(target)
        try:
            _warm_up(client)
            html = _request(client, first_url, headers={"Referer": BASE_URL})
            return client, target, html
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "fingerprint %s failed on %s — rotating: %s", target, first_url, exc
            )
            client.close()
    assert last_exc is not None
    raise last_exc


def _fetch_detail_rotating(
    client: cffi_requests.Session,
    current_target: str,
    url: str,
    referer: str,
) -> tuple[cffi_requests.Session, str, str]:
    """Fetch a detail page; on a CF gate, rotate through the other fingerprints.

    Returns ``(client, target, html)`` — the client may be a fresh one if a
    rotation cleared the gate (the retired client is closed). Raises
    ``CloudflareChallenge`` only if every fingerprint is gated. Never closes the
    caller's original client except when swapping it for a working replacement.
    """
    headers = {"Referer": referer}
    try:
        return client, current_target, _request(client, url, headers=headers)
    except CloudflareChallenge as first_cf:
        cf_exc: CloudflareChallenge = first_cf
    idx = IMPERSONATE_TARGETS.index(current_target)
    rotation = IMPERSONATE_TARGETS[idx + 1 :] + IMPERSONATE_TARGETS[:idx]
    for target in rotation:
        new_client = build_client(target)
        try:
            html = _request(new_client, url, headers=headers)
        except CloudflareChallenge as exc:
            cf_exc = exc
            new_client.close()
            continue
        except Exception:
            new_client.close()
            raise
        logger.info("detail CF cleared by rotating to %s: %s", target, url)
        client.close()
        return new_client, target, html
    raise cf_exc


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield parsed job posting dicts for the given Indeed listing URL.

    Stops early when a listing page returns no postings, ``limit`` is hit, or
    the whole listing page is Cloudflare-gated. A gated *detail* page is not
    fatal: the fingerprint is rotated and, if still gated, the detail is
    skipped — the crawl only aborts after ``CF_ABORT_THRESHOLD`` consecutive
    gated details (the session/IP is burned).

    Example usage:
    https://id.indeed.com/jobs?q=mobile+developer
    """
    owns_client = client is None
    original_client = client
    current_target = IMPERSONATE_TARGETS[0]
    consecutive_cf = 0
    yielded = 0
    try:
        for page_idx, listing_url in enumerate(iter_listing_pages(url, max_pages)):
            if page_idx == 0 and owns_client:
                # First fetch doubles as fingerprint selection: rotate through
                # IMPERSONATE_TARGETS until one isn't Cloudflare-gated, then
                # reuse that client for the rest of the crawl.
                try:
                    client, current_target, listing_html = _open_working_client(
                        listing_url
                    )
                except CloudflareChallenge as exc:
                    logger.error(
                        "all fingerprints CF-blocked on %s — aborting: %s",
                        listing_url,
                        exc,
                    )
                    return
                except Exception as exc:
                    logger.error("listing fetch failed: %s — %s", listing_url, exc)
                    return
            else:
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
                    client, current_target, detail_html = _fetch_detail_rotating(
                        client, current_target, detail_url, referer=listing_url
                    )
                    consecutive_cf = 0
                except CloudflareChallenge as exc:
                    consecutive_cf += 1
                    if consecutive_cf >= CF_ABORT_THRESHOLD:
                        logger.error(
                            "CF gate persists on %d consecutive details — aborting: %s",
                            consecutive_cf,
                            exc,
                        )
                        return
                    logger.warning(
                        "detail CF-gated on all fingerprints, skipping %s (%d/%d): %s",
                        detail_url,
                        consecutive_cf,
                        CF_ABORT_THRESHOLD,
                        exc,
                    )
                    continue
                except Exception as exc:
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
        if client is not None and (owns_client or client is not original_client):
            client.close()
