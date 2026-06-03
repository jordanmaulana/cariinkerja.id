"""HTML scraper for LinkedIn jobs (linkedin.com).

LinkedIn's interactive ``/jobs/search/`` page demands a sign-in to view more
than a handful of cards, but the **guest** endpoints return clean HTML
fragments with no login and no JS:

- listing: ``/jobs-guest/jobs/api/seeMoreJobPostings/search?<search params>&start=N``
- detail:  ``/jobs-guest/jobs/api/jobPosting/<jobId>``

Two-phase like the Indeed scraper: parse the listing for job cards (which
already carry title/company/location), then fetch each guest detail fragment
for the description + employment type.

LinkedIn rate-limits bots aggressively (HTTP ``429`` and the bot-block code
``999``); uses ``curl_cffi`` with Chrome TLS impersonation to pass the
fingerprint check. On a hard block this raises ``LinkedInBlock`` — at that
point the next step is slowing the crawl or rotating IPs.
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

logger = logging.getLogger(__name__)

BASE_URL = "https://www.linkedin.com"
GUEST_SEARCH = BASE_URL + "/jobs-guest/jobs/api/seeMoreJobPostings/search"
GUEST_DETAIL = BASE_URL + "/jobs-guest/jobs/api/jobPosting/{job_id}"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
TIMEOUT = 20.0
DEFAULT_SLEEP = 2.5
PAGE_SIZE = 10
RETRY_STATUSES = {429, 500, 502, 503, 504, 999}
MAX_RETRIES = 3
IMPERSONATE = "chrome131"

# Only these query params are meaningful to the guest search endpoint; the rest
# (origin, position, pageNum, currentJobId, trk, ...) are interactive-UI cruft.
SEARCH_PARAM_PREFIXES = ("f_",)
SEARCH_PARAM_KEYS = {
    "keywords",
    "geoId",
    "location",
    "locationId",
    "distance",
    "sortBy",
}

# Maps a normalized "Employment type" criteria *value* to a JobType. The guest
# fragment localizes both the criteria label and its value to Accept-Language,
# so we match on the (English + Indonesian) value text and ignore the label.
EMPLOYMENT_TYPE_MAP: dict[str, str] = {
    "FULL_TIME": JobType.FULL_TIME,
    "FULLTIME": JobType.FULL_TIME,
    "PENUH_WAKTU": JobType.FULL_TIME,
    "PART_TIME": JobType.PART_TIME,
    "PARTTIME": JobType.PART_TIME,
    "PARUH_WAKTU": JobType.PART_TIME,
    "CONTRACT": JobType.CONTRACT,
    "CONTRACTOR": JobType.CONTRACT,
    "TEMPORARY": JobType.CONTRACT,
    "KONTRAK": JobType.CONTRACT,
    "SEMENTARA": JobType.CONTRACT,
    "INTERN": JobType.INTERNSHIP,
    "INTERNSHIP": JobType.INTERNSHIP,
    "MAGANG": JobType.INTERNSHIP,
}

REMOTE_HINT_MAP: dict[str, str] = {
    "remote": RemoteOption.REMOTE,
    "jarak jauh": RemoteOption.REMOTE,
    "wfh": RemoteOption.REMOTE,
    "work from home": RemoteOption.REMOTE,
    "hybrid": RemoteOption.HYBRID,
    "hibrid": RemoteOption.HYBRID,
    "on-site": RemoteOption.ON_SITE,
    "on site": RemoteOption.ON_SITE,
    "di kantor": RemoteOption.ON_SITE,
    "wfo": RemoteOption.ON_SITE,
}


class LinkedInBlock(RuntimeError):
    """LinkedIn served a bot-block (HTTP 999 / auth wall) instead of content."""


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


def _request(client: cffi_requests.Session, url: str) -> str:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.get(url, allow_redirects=True)
            if resp.status_code == 999:
                raise LinkedInBlock(f"LinkedIn returned 999 (bot block) on {url}")
            if "/authwall" in (resp.url or "") or "/login" in (resp.url or ""):
                raise LinkedInBlock(f"redirected to auth wall on {url} -> {resp.url}")
            if resp.status_code in RETRY_STATUSES:
                raise RuntimeError(f"retryable status {resp.status_code}")
            resp.raise_for_status()
            return resp.text
        except LinkedInBlock:
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


def _guest_search_url(input_url: str, start: int) -> str:
    """Translate a user listing URL into the guest seeMore search endpoint.

    Keeps only the search-relevant query params (``keywords``, ``geoId``,
    ``location``, ``f_*`` filters, ``sortBy``); drops interactive-UI params.
    Idempotent if a guest URL is passed back in.
    """
    parsed = urlparse(input_url)
    kept: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query):
        if key == "start":
            continue
        if key in SEARCH_PARAM_KEYS or key.startswith(SEARCH_PARAM_PREFIXES):
            kept.append((key, value))
    kept.append(("start", str(start)))
    guest = urlparse(GUEST_SEARCH)
    return urlunparse(guest._replace(query=urlencode(kept)))


def iter_listing_pages(url: str, max_pages: int) -> Iterator[str]:
    """Yield up to ``max_pages`` guest search URLs, stepping ``start`` by 10."""
    for page_idx in range(max_pages):
        yield _guest_search_url(url, page_idx * PAGE_SIZE)


def _job_id_from_card(li) -> str | None:
    holder = li.select_one("[data-entity-urn]") or li.select_one("[data-job-id]")
    if holder is not None:
        urn = holder.get("data-entity-urn") or ""
        if ":" in urn:
            return urn.rsplit(":", 1)[-1].strip() or None
        jid = holder.get("data-job-id")
        if jid:
            return jid.strip() or None
    return None


def _text(li, selector: str) -> str | None:
    el = li.select_one(selector)
    if el is None:
        return None
    txt = el.get_text(" ", strip=True)
    return txt or None


def parse_listing(html: str) -> list[dict]:
    """Return job-card base dicts from a guest listing fragment.

    Each dict: ``{url, job_id, title, company, location}``. Title/company/
    location come straight off the card; the description is filled later from
    the detail fragment. Deduped by ``job_id``, order preserved.
    """
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    cards: list[dict] = []
    for li in soup.select("li"):
        link = li.select_one('a.base-card__full-link, a[href*="/jobs/view/"]')
        job_id = _job_id_from_card(li)
        if link is None and job_id is None:
            continue
        if job_id is None:
            href = (link.get("href") or "").split("?")[0]
            tail = href.rstrip("/").rsplit("-", 1)[-1]
            job_id = tail if tail.isdigit() else None
        if not job_id or job_id in seen:
            continue
        seen.add(job_id)
        url = (link.get("href") or "").split("?")[0] if link is not None else ""
        cards.append(
            {
                "url": url or f"{BASE_URL}/jobs/view/{job_id}",
                "job_id": job_id,
                "title": _text(li, ".base-search-card__title, h3"),
                "company": _text(li, ".base-search-card__subtitle, h4"),
                "location": _text(li, ".job-search-card__location"),
            }
        )
    return cards


def _employment_type_from_criteria(values: list[str]) -> str | None:
    """First criteria value that maps to a JobType, else None.

    The criteria label is localized so we can't key on "Employment type";
    instead we scan every value (Seniority/Function/Industry too) and return
    the first that matches a known employment-type term.
    """
    for value in values:
        key = value.strip().upper().replace("-", "_").replace(" ", "_")
        if key in EMPLOYMENT_TYPE_MAP:
            return EMPLOYMENT_TYPE_MAP[key]
    return None


def _map_remote_option(title: str, location: str, description: str) -> str | None:
    haystack = f"{title}\n{location}\n{description}".lower()
    for label, value in REMOTE_HINT_MAP.items():
        if label in haystack:
            return value
    return None


def _criteria_values(soup: BeautifulSoup) -> list[str]:
    out: list[str] = []
    for item in soup.select(".description__job-criteria-item"):
        val = item.select_one(".description__job-criteria-text, span")
        if val is not None:
            text = val.get_text(" ", strip=True)
            if text:
                out.append(text)
    return out


def parse_detail(html: str, base: dict) -> dict | None:
    """Merge description/job_type/remote_option from a detail fragment onto ``base``.

    Returns ``None`` if no description can be recovered.
    """
    soup = BeautifulSoup(html, "lxml")
    desc_el = soup.select_one(".show-more-less-html__markup, .description__text")
    description = desc_el.get_text("\n", strip=True) if desc_el else None
    if not description:
        logger.warning("LinkedIn detail missing description: %s", base.get("url"))
        return None

    job_type = _employment_type_from_criteria(_criteria_values(soup))

    title = base.get("title") or ""
    company = base.get("company")
    location = base.get("location")
    if not title:
        t = soup.select_one(".top-card-layout__title, h1, h2.topcard__title")
        if t is not None:
            title = t.get_text(" ", strip=True)
    if not company:
        c = soup.select_one(".topcard__org-name-link, .top-card-layout__card a")
        if c is not None:
            company = c.get_text(" ", strip=True)
    if not location:
        loc = soup.select_one(".topcard__flavor--bullet")
        if loc is not None:
            location = loc.get_text(" ", strip=True)

    if not title:
        logger.warning("LinkedIn job missing title: %s", base.get("url"))
        return None

    remote_option = _map_remote_option(title, location or "", description)

    return {
        "url": base["url"],
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
    """Yield parsed job posting dicts for the given LinkedIn listing URL.

    Stops early when a listing page returns no cards, ``limit`` is hit, or a
    hard bot-block is detected (``LinkedInBlock`` — retrying without slowing
    down or rotating IP won't help, so abort).

    Example usage:
    https://www.linkedin.com/jobs/search/?keywords=flutter&geoId=102478259
    """
    owns_client = client is None
    client = client or build_client()
    yielded = 0
    try:
        for listing_url in iter_listing_pages(url, max_pages):
            try:
                listing_html = _request(client, listing_url)
            except LinkedInBlock as exc:
                logger.error(
                    "LinkedIn block on listing %s — aborting: %s", listing_url, exc
                )
                break
            except Exception as exc:
                logger.error("listing fetch failed: %s — %s", listing_url, exc)
                break
            cards = parse_listing(listing_html)
            if not cards:
                break
            for card in cards:
                if limit is not None and yielded >= limit:
                    return
                time.sleep(sleep + random.uniform(0, 0.3))
                detail_url = GUEST_DETAIL.format(job_id=card["job_id"])
                try:
                    detail_html = _request(client, detail_url)
                except LinkedInBlock as exc:
                    logger.error(
                        "LinkedIn block on detail %s — aborting: %s", detail_url, exc
                    )
                    return
                except Exception as exc:
                    logger.error("detail fetch failed: %s — %s", detail_url, exc)
                    continue
                parsed = parse_detail(detail_html, card)
                if parsed is None:
                    continue
                yielded += 1
                yield parsed
            time.sleep(sleep + random.uniform(0, 0.3))
    finally:
        if owns_client:
            client.close()
