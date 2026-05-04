from __future__ import annotations

import logging

from apify_client import ApifyClient
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from profiles.models import Profile
from profiles.services import LinkedInIngest, ingest_linkedin

logger = logging.getLogger(__name__)

ACTOR_ID = "harvestapi/linkedin-profile-scraper"


def crawl_and_ingest_linkedin(profile: Profile) -> LinkedInIngest | None:
    if not profile.linkedin_url:
        raise ValueError("profile.linkedin_url is required")
    if not settings.APIFY_TOKEN:
        raise RuntimeError("APIFY_TOKEN is not configured")

    client = ApifyClient(settings.APIFY_TOKEN)
    run_input = {
        "profileScraperMode": "Profile details no email ($4 per 1k)",
        "queries": [profile.linkedin_url],
    }
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    item = next(client.dataset(run["defaultDatasetId"]).iterate_items(), None)
    if not item:
        logger.warning("apify returned no items for %s", profile.linkedin_url)
        return None

    raw_text = _flatten_apify_item(item)

    update_fields = ["linkedin_raw", "updated_on"]
    profile.linkedin_raw = raw_text

    try:
        result = ingest_linkedin(raw_text)
    except Exception:
        with transaction.atomic():
            profile.save(update_fields=update_fields)
        raise

    profile.full_profile = result.cleaned_full_profile or None
    profile.open_to_work = result.open_to_work
    profile.linkedin_quality_ok = not result.is_sparse
    profile.linkedin_quality_reason = result.sparse_reason or result.quality_notes or ""
    profile.linkedin_ingested_at = timezone.now()
    update_fields += [
        "full_profile",
        "open_to_work",
        "linkedin_quality_ok",
        "linkedin_quality_reason",
        "linkedin_ingested_at",
    ]
    with transaction.atomic():
        profile.save(update_fields=update_fields)
    return result


def _coerce_location(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("linkedinText", "text", "name"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        parsed = value.get("parsed")
        if isinstance(parsed, dict):
            v = parsed.get("text")
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _flatten_apify_item(item: dict) -> str:
    parts: list[str] = []

    name = (
        item.get("fullName")
        or item.get("name")
        or " ".join(filter(None, [item.get("firstName"), item.get("lastName")])).strip()
    )
    if name:
        parts.append(f"Name: {name}")

    headline = item.get("headline")
    if headline:
        parts.append(f"Headline: {headline}")

    location = _coerce_location(
        item.get("addressWithCountry")
        or item.get("location")
        or item.get("addressWithoutCountry")
    )
    if location:
        parts.append(f"Location: {location}")

    for flag_key in ("openToWork", "isOpenToWork", "open_to_work"):
        if flag_key in item:
            parts.append(f"Open To Work: {'yes' if item[flag_key] else 'no'}")
            break

    about = item.get("about") or item.get("summary")
    if about:
        parts.append(f"About:\n{about}")

    experiences = (
        item.get("experiences") or item.get("experience") or item.get("positions") or []
    )
    exp_lines = []
    for exp in experiences:
        if not isinstance(exp, dict):
            continue
        title = exp.get("title") or exp.get("position") or ""
        company = exp.get("companyName") or exp.get("company") or ""
        duration = (
            exp.get("duration") or exp.get("dateRange") or exp.get("period") or ""
        )
        header = f"- {title} @ {company}".rstrip(" @").rstrip()
        if duration:
            header += f" ({duration})"
        exp_lines.append(header)
        desc = exp.get("description") or exp.get("summary")
        if desc:
            exp_lines.append(f"  {desc.strip()}")
    if exp_lines:
        parts.append("Experience:\n" + "\n".join(exp_lines))

    educations = item.get("educations") or item.get("education") or []
    edu_lines = []
    for edu in educations:
        if not isinstance(edu, dict):
            continue
        school = edu.get("schoolName") or edu.get("school") or ""
        degree = edu.get("degree") or edu.get("degreeName") or ""
        field = edu.get("fieldOfStudy") or edu.get("field") or ""
        dates = edu.get("dateRange") or edu.get("period") or edu.get("duration") or ""
        bits = [b for b in [degree, field] if b]
        line = f"- {school}"
        if bits:
            line += f" — {', '.join(bits)}"
        if dates:
            line += f" ({dates})"
        edu_lines.append(line)
        desc = edu.get("description")
        if desc:
            edu_lines.append(f"  {desc.strip()}")
    if edu_lines:
        parts.append("Education:\n" + "\n".join(edu_lines))

    skills = item.get("skills") or []
    skill_names = []
    for s in skills:
        if isinstance(s, str):
            skill_names.append(s)
        elif isinstance(s, dict):
            n = s.get("name") or s.get("title")
            if n:
                skill_names.append(n)
    if skill_names:
        parts.append("Skills: " + ", ".join(skill_names))

    return "\n\n".join(parts).strip()
