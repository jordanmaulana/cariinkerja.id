import logging
from urllib.parse import quote_plus

from django.conf import settings
from django.db import transaction
from openai import OpenAI
from pydantic import BaseModel

from profiles.consts import Source, Status

logger = logging.getLogger(__name__)


class LinkedInIngest(BaseModel):
    cleaned_full_profile: str
    is_sparse: bool
    sparse_reason: str = ""
    open_to_work: bool
    quality_notes: str


SYSTEM_PROMPT = (
    "You normalize a LinkedIn profile that a recruiter pasted from their browser. "
    "The input is messy: HTML cruft, repeated nav strings, the candidate's own copy, "
    "and possibly fragments of OTHER people's profiles (sidebars, "
    '"People you may know", endorsement rows). Your job:\n\n'
    "1. Return ONLY the candidate's own profile content as cleaned_full_profile. "
    'Strip nav, sidebars, endorsement rows, "show more" tokens, emoji-only lines. '
    "Preserve section structure (About / Experience / Education / Skills) as plain "
    "text with blank-line separators.\n\n"
    "2. Score sparseness: is_sparse=True ONLY if the profile is unusable for job "
    "matching — e.g., job titles with no descriptions, no About section, fewer than "
    "~150 words of substantive content. A short but substantive profile is NOT "
    'sparse. Put a concrete reason in sparse_reason (e.g., "5 roles listed but zero '
    'have descriptions; no About section"). Leave sparse_reason empty when '
    "is_sparse=False.\n\n"
    "3. Detect Open to Work ONLY for the candidate themselves. Set open_to_work=True "
    'only if you see (a) the literal "#OPEN_TO_WORK" hashtag, (b) the phrase '
    '"Open to Work" attached to the candidate\'s own headline/photo section, or '
    '(c) a "Looking for [role]" banner clearly attributed to the candidate. Do NOT '
    "set True from stray mentions in someone else's recommendation, endorsement, or "
    "sidebar content. When unsure, set False.\n\n"
    '4. quality_notes: 1-2 sentences for the recruiter (e.g., "Strong tech stack '
    'detail, but no quantified outcomes").'
)


def ingest_linkedin(raw: str) -> LinkedInIngest:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.parse(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw[:60_000]},
        ],
        response_format=LinkedInIngest,
        timeout=30,
    )
    return resp.choices[0].message.parsed


def maybe_start_free_crawl(preference) -> bool:
    """Auto-fill Indeed crawl config + queue one free crawl run.

    Idempotent. Returns True if crawl was queued.
    Conditions: status=WAITING_ADMIN, profile.full_profile present, no
    existing crawl_url, has title.
    """
    from assessment.tasks import run_free_crawl

    if preference.status != Status.WAITING_ADMIN:
        return False
    if preference.crawl_url:
        return False
    if not preference.title:
        return False
    profile = preference.profile
    if not profile.full_profile:
        return False

    preference.crawl_url = (
        f"https://id.indeed.com/jobs?q={quote_plus(preference.title)}"
    )
    preference.crawl_source = Source.INDEED
    preference.save(update_fields=["crawl_url", "crawl_source", "updated_on"])
    transaction.on_commit(lambda: run_free_crawl.delay(preference.id))
    logger.info(
        "free crawl queued for preference=%s profile=%s",
        preference.id,
        profile.id,
    )
    return True
