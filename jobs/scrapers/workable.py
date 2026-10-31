"""Workable source: one public XML feed, synced into ``Job``, then matched locally.

Workable publishes every published job from every customer in a single feed
(``https://www.workable.com/boards/workable.xml``, ~170k jobs, ~1.1 GB raw /
~145 MB gzipped, oldest first, refreshed hourly). It takes no filter params,
so there is no per-preference search:

* ``sync_feed()`` (Celery task ``jobs.tasks.sync_workable_feed``, every few
  hours) streams the whole feed, keeps Indonesia jobs plus remote jobs
  anchored in APAC, upserts them into ``Job`` and marks Workable jobs that
  left the feed as expired.
* ``crawl(url)`` makes **no network call**: it matches the preference title
  against those synced rows. The crawl URL is Workable's human search page
  (``https://jobs.workable.com/search?query=...``) so admins can click it
  for a preview; only its ``query`` / ``location`` params are used.

Feed rules (help.workable.com, "Utilizing the XML Job Feed"): job URLs must
stay unchanged (candidate attribution), so ``Job.url`` is the feed ``url``.
The server cuts a slow download at ~60 s — compressed HTTP/1.1 finishes well
inside that; uncompressed HTTP/2 did not. A few pulls in an hour get a 429
with ``Retry-After`` ≈ 1 h, so sync at most hourly and never auto-retry.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from email.utils import parsedate_to_datetime
from typing import Iterable, Iterator
from urllib.parse import parse_qsl, urlparse

from bs4 import BeautifulSoup
from curl_cffi import CurlHttpVersion
from curl_cffi import requests as cffi_requests
from django.db import transaction
from django.utils import timezone
from lxml import etree

from jobs.consts import JobType, RemoteOption
from jobs.models import Job
from jobs.scrapers.filters import is_blocked_company
from profiles.consts import Source

logger = logging.getLogger(__name__)

FEED_URL = "https://www.workable.com/boards/workable.xml"
FEED_TIMEOUT = 300.0
IMPERSONATE = "chrome131"
# Hundreds of 2021-22 postings are still "published"; ignore stale ones.
MAX_AGE_DAYS = 60

# Remote jobs anchored here are kept besides Indonesia jobs (product decision).
APAC_REMOTE = {
    "SG", "MY", "PH", "TH", "VN", "KH", "MM", "LA", "BN", "TL",
    "AU", "NZ", "JP", "KR", "HK", "TW", "CN", "IN", "BD", "PK", "LK", "NP",
}  # fmt: skip

JOBTYPE_MAP: dict[str, str] = {
    "Full-time": JobType.FULL_TIME,
    "Part-time": JobType.PART_TIME,
    "Contract": JobType.CONTRACT,
    "Temporary": JobType.CONTRACT,
}

UPSERT_FIELDS = [
    "title",
    "company",
    "description",
    "location",
    "job_type",
    "remote_option",
    "expires_at",
    "updated_on",
]


def build_client() -> cffi_requests.Session:
    # The impersonated browser asks for gzip/br and curl decodes it.
    session = cffi_requests.Session(impersonate=IMPERSONATE, timeout=FEED_TIMEOUT)
    session.headers.update({"Accept": "application/xml"})
    return session


def _drain(parser) -> Iterator[dict[str, str]]:
    for _, el in parser.read_events():
        yield {child.tag: (child.text or "").strip() for child in el}
        # Free parsed jobs, or the whole 1 GB tree builds up in memory.
        el.clear()
        while el.getprevious() is not None:
            del el.getparent()[0]


def iter_feed(chunks: Iterable[bytes]) -> Iterator[dict[str, str]]:
    """Yield one ``{field: text}`` dict per ``<job>`` from raw feed bytes.

    Raises ``lxml.etree.XMLSyntaxError`` if the document is cut short.
    """
    # Untrusted XML: never expand entities.
    parser = etree.XMLPullParser(events=("end",), tag="job", resolve_entities=False)
    for chunk in chunks:
        parser.feed(chunk)
        yield from _drain(parser)
    parser.close()
    yield from _drain(parser)


def in_scope(raw: dict) -> bool:
    country = raw.get("country")
    return country == "ID" or (raw.get("remote") == "true" and country in APAC_REMOTE)


def _posted_at(raw: dict):
    try:
        return parsedate_to_datetime(raw.get("date", ""))
    except (TypeError, ValueError):
        return None


def parse_job(raw: dict) -> dict | None:
    """Map one feed job to a Job-shaped dict; None if unusable."""
    url = raw.get("url")
    title = raw.get("title") or ""
    html = raw.get("description") or ""
    description = BeautifulSoup(html, "lxml").get_text("\n", strip=True) if html else ""
    if not url or not title or not description:
        logger.warning(
            "job missing url/title/description: ref=%s", raw.get("referencenumber")
        )
        return None
    company = raw.get("company") or None
    if is_blocked_company(company):
        return None

    if raw.get("country") == "ID":
        parts = (raw.get("city"), raw.get("state"), "Indonesia")
        location = ", ".join(dict.fromkeys(p for p in parts if p))
    else:
        # ponytail: a remote job's feed country is where it is anchored, not
        # who may apply. The relevance gate reads a remote job's location as an
        # applicant restriction, so "Philippines" would reject every PH job;
        # leaving it blank makes the gate judge residency from the description.
        # Add a separate office-location field if the anchor is needed in the UI.
        location = None

    if raw.get("experience") == "Internship":
        job_type = JobType.INTERNSHIP
    else:
        job_type = JOBTYPE_MAP.get(raw.get("jobtype") or "")
    return {
        "url": url,
        "title": title[:255],
        "company": company[:255] if company else None,
        "description": description,
        "location": location[:255] if location else None,
        "job_type": job_type,
        # The feed can't tell on-site from hybrid; "unspecified" avoids a false
        # mismatch penalty in the assessor.
        "remote_option": RemoteOption.REMOTE if raw.get("remote") == "true" else None,
    }


def sync_feed(client: cffi_requests.Session | None = None) -> dict:
    """Download the feed and upsert in-scope jobs into ``Job``.

    Writes nothing unless the whole feed parsed, so a cut download can't
    expire the jobs it never reached.
    """
    owns_client = client is None
    client = client or build_client()
    now = timezone.now()
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    in_feed = 0
    seen: set[str] = set()  # every in-scope URL still in the feed, any age
    rows: dict = {}
    try:
        resp = client.get(
            FEED_URL,
            stream=True,
            http_version=CurlHttpVersion.V1_1,
            timeout=FEED_TIMEOUT,
        )
        try:
            resp.raise_for_status()
            for raw in iter_feed(resp.iter_content()):
                in_feed += 1
                if not in_scope(raw) or not raw.get("url"):
                    continue
                seen.add(raw["url"])
                posted = _posted_at(raw)
                if posted is None or posted < cutoff:
                    continue
                parsed = parse_job(raw)
                if parsed is None:
                    continue
                # Remote postings get cloned per country under new URLs: keep
                # one, preferring the Indonesia copy (the one with a location).
                if parsed["remote_option"] == RemoteOption.REMOTE:
                    key = ((parsed["company"] or "").lower(), parsed["title"].lower())
                else:
                    key = parsed["url"]
                if key not in rows or not rows[key]["location"]:
                    rows[key] = parsed
        finally:
            resp.close()
    finally:
        if owns_client:
            client.close()

    with transaction.atomic():
        # Feed order is oldest first, so created_on follows posting date.
        Job.objects.bulk_create(
            [Job(source=Source.WORKABLE, expires_at=None, **p) for p in rows.values()],
            update_conflicts=True,
            unique_fields=["url"],
            update_fields=UPSERT_FIELDS,
            batch_size=500,
        )
        open_urls = set(
            Job.objects.filter(
                source=Source.WORKABLE, expires_at__isnull=True
            ).values_list("url", flat=True)
        )
        expired = Job.objects.filter(url__in=open_urls - seen).update(expires_at=now)
    result = {
        "in_feed": in_feed,
        "in_scope": len(seen),
        "upserted": len(rows),
        "expired": expired,
    }
    logger.info("workable sync: %s", result)
    return result


def crawl(
    url: str,
    *,
    max_pages: int = 1,
    sleep: float = 0.0,
    limit: int | None = None,
    client: cffi_requests.Session | None = None,
) -> Iterator[dict]:
    """Yield synced Workable jobs whose title matches the URL's ``query``.

    No network call. ``location=Indonesia`` limits matches to Indonesia jobs
    (drops the APAC remote pool). ``max_pages`` / ``sleep`` / ``client`` are
    accepted for the shared scraper signature and ignored.

    Example usage:
    https://jobs.workable.com/search?query=flutter+developer&location=Indonesia
    """
    params = dict(parse_qsl(urlparse(url).query))
    words = [w for w in re.split(r"\W+", params.get("query", "").lower()) if len(w) > 1]
    if not words:
        logger.warning("no query in workable crawl url: %s", url)
        return
    synced = Job.objects.filter(source=Source.WORKABLE)
    if not synced.exists():
        logger.warning(
            "no Workable jobs synced yet — run jobs.tasks.sync_workable_feed"
        )
        return
    qs = synced.filter(expires_at__isnull=True)
    if params.get("location") == "Indonesia":
        qs = qs.filter(location__icontains="Indonesia")
    # ponytail: every title word must appear, no synonyms ("Mobile Developer"
    # misses "Flutter Engineer"). Move to full-text search if recall is poor.
    for w in words:
        qs = qs.filter(title__icontains=w)
    for job in qs.order_by("-created_on")[:limit]:
        yield {
            "url": job.url,
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "location": job.location,
            "job_type": job.job_type,
            "remote_option": job.remote_option,
        }
