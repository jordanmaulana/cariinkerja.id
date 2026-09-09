"""Scraper for Karirhub / SIAPkerja (karirhub.kemnaker.go.id).

The Indonesian Ministry of Manpower's public job portal. Employers are verified
through the mandatory WLKP reporting pipeline, so the postings carry more
provenance than a commercial board's — the mix skews administrative and
blue-collar rather than tech.

Two-phase, both phases against the portal's public JSON API: search vacancies,
then fetch each one for its description. The API is what the site's own header
search calls, and it honours a ``keyword`` — so a crawl URL carrying
``?keyword=`` actually filters.

Neither phase reads the rendered pages, for two reasons. The listing page
server-renders eight featured vacancies and searches client-side, so every
Preference would crawl the same eight postings. And the detail pages are Next.js
App Router documents whose props arrive as an RSC flight payload in which a long
field is often a ``$26``-style pointer into another chunk — parsing them yielded
a placeholder instead of the description for ~20% of a live sample (2026-09-09),
where the API returned the full text every time. The stored ``url`` is still the
human-readable page, since that is where the candidate is sent.

Its robots.txt is 1,248 bytes of pure comments with no directives at all — a
Cloudflare Content Signals template nobody configured — and the API host serves
no robots.txt at all, so under RFC 9309 everything is permitted by default. Both
serve an identifying bot User-Agent without complaint (verified 2026-09-09).
"""

from __future__ import annotations

import logging
import random
import time
from typing import Iterator
from urllib.parse import parse_qsl, urlencode, urlparse

import httpx
from bs4 import BeautifulSoup

from jobs.consts import BOT_USER_AGENT, JobType, RemoteOption
from jobs.scrapers.filters import is_blocked_company
from jobs.url_builders import slugify_title

logger = logging.getLogger(__name__)

BASE_URL = "https://karirhub.kemnaker.go.id"
DETAIL_PATH = "/lowongan-dalam-negeri/lowongan/"
LIST_API = (
    "https://api.kemnaker.go.id/karirhub/vacancy/v2/published-industrial-vacancies"
)
ACCEPT_LANGUAGE = "id-ID,id;q=0.9,en;q=0.8"
TIMEOUT = 20.0
DEFAULT_SLEEP = 1.5
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
# API page-size ceiling: limit=100 is rejected 422 "validation.max.numeric".
PAGE_LIMIT = 50

# Karirhub `job_type.name` values → our JobType. Indonesian and English labels
# both occur across the portal.
JOB_TYPE_FROM_LABEL: dict[str, str] = {
    "full time": JobType.FULL_TIME,
    "penuh waktu": JobType.FULL_TIME,
    "part time": JobType.PART_TIME,
    "paruh waktu": JobType.PART_TIME,
    "contract": JobType.CONTRACT,
    "kontrak": JobType.CONTRACT,
    "freelance": JobType.PART_TIME,
    "internship": JobType.INTERNSHIP,
    "magang": JobType.INTERNSHIP,
}

# `vacancyable.work_arrangement` values → our RemoteOption.
REMOTE_FROM_LABEL: dict[str, str] = {
    "remote": RemoteOption.REMOTE,
    "wfh": RemoteOption.REMOTE,
    "jarak jauh": RemoteOption.REMOTE,
    "hybrid": RemoteOption.HYBRID,
    "hibrida": RemoteOption.HYBRID,
    "onsite": RemoteOption.ON_SITE,
    "on site": RemoteOption.ON_SITE,
    "on_site": RemoteOption.ON_SITE,
    "wfo": RemoteOption.ON_SITE,
    "di kantor": RemoteOption.ON_SITE,
}


def build_client() -> httpx.Client:
    """An honest, self-identifying client — nothing here is being circumvented."""
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


def _list_api_url(input_url: str, page: int, per_page: int = PAGE_LIMIT) -> str:
    """Translate a karirhub.kemnaker.go.id listing URL into a vacancy-API URL.

    Only ``keyword`` carries over — it is the one filter our crawl URLs and the
    API agree on. No keyword yields the unfiltered list, which is what the
    crawl-health target wants.
    """
    keyword = dict(parse_qsl(urlparse(input_url).query)).get("keyword")
    params: list[tuple[str, str]] = [("limit", str(per_page)), ("page", str(page))]
    if keyword:
        params.append(("keyword", keyword))
    return f"{LIST_API}?{urlencode(params)}"


def parse_listing(payload: dict) -> list[dict]:
    """Return deduped ``{"id", "url"}`` entries for a search response payload.

    The search API carries no slug, so the page URL is rebuilt from the title.
    The site resolves a vacancy by its trailing UUID and renders the right
    posting even when the slug is wrong or absent (verified 2026-09-09), so the
    slug is cosmetic — it is kept only so the stored URL reads like a real one.
    """
    seen: set[str] = set()
    entries: list[dict] = []
    for record in payload.get("data") or []:
        vacancy_id = record.get("id")
        if not vacancy_id or vacancy_id in seen:
            continue
        seen.add(vacancy_id)
        slug = slugify_title(record.get("title") or "")
        tail = f"{slug}-{vacancy_id}" if slug else vacancy_id
        entries.append({"id": vacancy_id, "url": f"{BASE_URL}{DETAIL_PATH}{tail}"})
    return entries


def _last_page(payload: dict) -> int:
    return (payload.get("meta") or {}).get("last_page") or 0


def _html_to_text(*parts: str | None) -> str:
    html = "\n\n".join(p for p in parts if p)
    if not html:
        return ""
    return BeautifulSoup(html, "lxml").get_text("\n", strip=True)


def _map_job_type(job_type: dict | None) -> str | None:
    name = (job_type or {}).get("name")
    if not name:
        return None
    mapped = JOB_TYPE_FROM_LABEL.get(name.strip().lower())
    if mapped is None:
        logger.warning("unmapped job_type: %r", name)
    return mapped


def _map_remote_option(vacancyable: dict | None) -> str | None:
    arrangement = (vacancyable or {}).get("work_arrangement")
    if not arrangement:
        return None
    mapped = REMOTE_FROM_LABEL.get(str(arrangement).strip().lower())
    if mapped is None:
        logger.warning("unmapped work_arrangement: %r", arrangement)
    return mapped


def parse_detail(vacancy: dict, url: str) -> dict | None:
    """Parse a vacancy-detail API object into a Job-shaped dict.

    ``url`` is the human-readable page the candidate is sent to, not the API URL
    the object came from. Returns ``None`` when the object lacks a title or
    description. Reads only ``employer.name``; no recruiter-identifying field is
    carried through, and a vacancy flagged ``confidential`` yields no company
    name at all.
    """
    title = (vacancy.get("title") or "").strip()
    description = _html_to_text(
        vacancy.get("description"), vacancy.get("qualification")
    )
    if not title or not description:
        logger.warning("vacancy missing title/description: %s", url)
        return None

    company = None
    if not vacancy.get("confidential"):
        company = (vacancy.get("employer") or {}).get("name")
    location = (vacancy.get("region") or {}).get("name")

    return {
        "url": url,
        "title": title[:255],
        "company": (company[:255] if company else None),
        "description": description,
        "location": (location[:255] if location else None),
        "job_type": _map_job_type(vacancy.get("job_type")),
        "remote_option": _map_remote_option(vacancy.get("vacancyable")),
    }


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = DEFAULT_SLEEP,
    limit: int | None = None,
    client: httpx.Client | None = None,
) -> Iterator[dict]:
    """Yield parsed job posting dicts for the given Karirhub listing URL.

    Vacancies are searched through ``LIST_API`` (honouring a ``?keyword=`` on the
    input URL) and then fetched one by one for their descriptions. Stops early
    when a page returns nothing, the API's ``last_page`` is reached, or ``limit``
    is hit.

    Example usage:
    https://karirhub.kemnaker.go.id/lowongan-dalam-negeri
    """
    owns_client = client is None
    client = client or build_client()
    page_size = min(limit, PAGE_LIMIT) if limit else PAGE_LIMIT
    yielded = 0
    seen: set[str] = set()
    try:
        for page in range(1, max_pages + 1):
            try:
                payload = _request_json(client, _list_api_url(url, page, page_size))
            except Exception as exc:
                logger.error("listing fetch failed: page=%d — %s", page, exc)
                break
            entries = parse_listing(payload)
            if not entries:
                logger.warning("no vacancies returned for %s (page %d)", url, page)
                break
            fresh = [e for e in entries if e["url"] not in seen]
            seen.update(e["url"] for e in fresh)
            for entry in fresh:
                if limit is not None and yielded >= limit:
                    return
                time.sleep(sleep + random.uniform(0, 0.3))
                try:
                    detail = _request_json(client, f"{LIST_API}/{entry['id']}")
                except Exception as exc:
                    logger.error("detail fetch failed: %s — %s", entry["url"], exc)
                    continue
                parsed = parse_detail(detail.get("data") or {}, entry["url"])
                if parsed is None:
                    continue
                if is_blocked_company(parsed.get("company")):
                    continue
                yielded += 1
                yield parsed
            if page >= _last_page(payload):
                break
            time.sleep(sleep + random.uniform(0, 0.3))
    finally:
        if owns_client:
            client.close()
