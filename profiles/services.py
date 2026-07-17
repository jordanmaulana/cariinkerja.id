import logging
import re

from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, Field

from jobs.url_builders import build_crawl_urls
from profiles.consts import Status

logger = logging.getLogger(__name__)


class LinkedInIngest(BaseModel):
    # Declared first on purpose: structured-output field order is generation
    # order, so the model reads skills straight off the raw input before it
    # rewrites the profile text it must leave them out of.
    skills: list[str] = Field(default_factory=list)
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
    "1. skills: every skill the CANDIDATE lists or clearly demonstrates, as short "
    "names (English technical terms OK). LinkedIn glues each skill to endorsement "
    'noise — e.g. "Python\\nEndorsed by 12 people", "React · 8 endorsements", '
    '"Kubernetes\\nEndorsed by Jane Doe and 4 others". Keep the SKILL NAME and drop '
    "the endorsement text around it — never drop the row itself. Also include skills "
    'named in the About/Experience text, and every entry of a "Skills: a, b, c" line '
    "if the input already has one. Do not invent skills. Do not include other "
    "people's skills from sidebars. Deduplicate. Return an empty list only if the "
    "profile truly names no skills.\n\n"
    "2. Return ONLY the candidate's own profile content as cleaned_full_profile. "
    'Strip nav, sidebars, endorser names, "show more" tokens, emoji-only lines. '
    "Preserve section structure (About / Experience / Education) as plain text with "
    "blank-line separators. Do NOT include a Skills section in cleaned_full_profile "
    "— skills belong in the `skills` field ONLY (see 1); they are appended "
    "separately.\n\n"
    "3. Score sparseness: is_sparse=True ONLY if the profile is unusable for job "
    "matching — e.g., job titles with no descriptions, no About section, fewer than "
    "~150 words of substantive content. A short but substantive profile is NOT "
    'sparse. Put a concrete reason in sparse_reason (e.g., "5 roles listed but zero '
    'have descriptions; no About section"). Leave sparse_reason empty when '
    "is_sparse=False. Judge the profile as a whole, including the skills you "
    "extracted in 1, not only the text you placed in cleaned_full_profile.\n\n"
    "4. Detect Open to Work ONLY for the candidate themselves. Set open_to_work=True "
    'only if you see (a) the literal "#OPEN_TO_WORK" hashtag, (b) the phrase '
    '"Open to Work" attached to the candidate\'s own headline/photo section, or '
    '(c) a "Looking for [role]" banner clearly attributed to the candidate. Do NOT '
    "set True from stray mentions in someone else's recommendation, endorsement, or "
    "sidebar content. When unsure, set False.\n\n"
    '5. quality_notes: 1-2 sentences for the recruiter (e.g., "Strong tech stack '
    'detail, but no quantified outcomes").'
)

# Matches a block heading like "Skills", "Skills:", "Skills & Endorsements" —
# but not prose such as "Skills and Tools I use daily:".
_SKILLS_HEADING_RE = re.compile(
    r"^skills(?:\s*(?:&|and)\s*endorsements)?\s*:.*$"
    r"|^skills(?:\s*(?:&|and)\s*endorsements)?\s*$",
    re.IGNORECASE,
)

_MAX_RAW_CHARS = 60_000
_TAIL_CHARS = 20_000
_TRUNCATION_MARKER = "\n\n[...TRUNCATED MIDDLE...]\n\n"


def _normalize_skills(names: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for name in names or []:
        cleaned = (name or "").strip()
        if not cleaned or cleaned.casefold() in seen:
            continue
        seen.add(cleaned.casefold())
        out.append(cleaned)
    return out


def render_skills_block(names: list[str]) -> str:
    normalized = _normalize_skills(names)
    return "Skills\n" + ", ".join(normalized) if normalized else ""


def _strip_skills_blocks(text: str) -> str:
    kept = []
    for block in re.split(r"\n\s*\n", text):
        lines = block.strip().splitlines()
        if not lines or _SKILLS_HEADING_RE.match(lines[0].strip()):
            continue
        kept.append(block.strip())
    return "\n\n".join(kept)


def render_full_profile(cleaned: str, skills: list[str]) -> str:
    """Canonical shape: profile text, then one Skills block as the last section.

    The Skills block is rendered here rather than left to the model. The Apify
    path only ever worked because _flatten_apify_item builds the same line in
    Python; a browser paste has no such line, so the model dropped skills along
    with the endorsement noise they are glued to.
    """
    body = _strip_skills_blocks((cleaned or "").strip())
    block = render_skills_block(skills)
    if not block:
        return body
    return f"{body}\n\n{block}" if body else block


def _truncate_for_llm(
    raw: str, limit: int = _MAX_RAW_CHARS, tail: int = _TAIL_CHARS
) -> str:
    """Keep the head AND the tail — LinkedIn puts Skills at the bottom of a page."""
    if len(raw) <= limit:
        return raw
    head = limit - tail - len(_TRUNCATION_MARKER)
    return raw[:head] + _TRUNCATION_MARKER + raw[-tail:]


def ingest_linkedin(raw: str) -> LinkedInIngest:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.parse(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _truncate_for_llm(raw)},
        ],
        response_format=LinkedInIngest,
        timeout=30,
    )
    result = resp.choices[0].message.parsed
    result.cleaned_full_profile = render_full_profile(
        result.cleaned_full_profile, result.skills
    )
    return result


def prepare_preference_for_payment(preference, *, require_full_profile=True) -> bool:
    """Auto-fill crawl config + advance a new preference to WAITING_PAYMENT.

    Idempotent. Returns True if the preference was advanced. No crawl runs
    here (the free crawl on registration is disabled) — the first real crawl
    happens after payment via core.payments.subscriptions.activate_subscription.
    Conditions: status=WAITING_ADMIN, no existing crawl_urls, has title, and
    (unless require_full_profile=False) profile.full_profile present.

    The registration path passes require_full_profile=False so a brand-new
    preference becomes payable immediately, before LinkedIn ingest completes.
    """
    if preference.status != Status.WAITING_ADMIN:
        return False
    if preference.crawl_urls:
        return False
    if not preference.title:
        return False
    profile = preference.profile
    if require_full_profile and not profile.full_profile:
        return False

    preference.crawl_urls = build_crawl_urls(
        preference.title, preference.job_type, preference.remote_option
    )
    preference.status = Status.WAITING_PAYMENT
    preference.save(update_fields=["crawl_urls", "status", "updated_on"])
    logger.info(
        "preference=%s advanced to WAITING_PAYMENT (free crawl disabled) profile=%s",
        preference.id,
        profile.id,
    )
    return True
