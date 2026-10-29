from django.conf import settings
from pydantic import BaseModel, Field

from core.openai import get_prompt_manager
from jobs.consts import RemoteOption


class SkillAssessment(BaseModel):
    soft_skill_match: list[str]
    soft_skill_gap: list[str]
    hard_skill_match: list[str]
    hard_skill_gap: list[str]
    score: int = Field(ge=0, le=100)
    verdict: str


class RelevanceCheck(BaseModel):
    is_relevant: bool
    reason: str


class _RelevanceAnswer(BaseModel):
    """What the cheap model answers; check_relevance combines it in code.

    Separate yes/no questions because the model mixed them up when asked for
    one combined verdict (and kept reading 'work from our Singapore office'
    as a residency rule).
    """

    same_field: bool
    residency_excludes_indonesia: bool
    requires_foreign_work_authorization: bool
    reason: str


SYSTEM_PROMPT = (
    "You assess candidate fit for a job posting. "
    "Return matched and missing soft & hard skills, a 0-100 score, "
    "and a short verdict (1-3 sentences) explaining the score.\n\n"
    "CRITICAL LANGUAGE RULE: The `verdict` field MUST be written in "
    "Bahasa Indonesia, kasual, menggunakan kata ganti 'kamu'. "
    "Do NOT write the verdict in English under any circumstance, even if "
    "the job posting or candidate context is in English. "
    "Skill fields (soft_skill_match, soft_skill_gap, hard_skill_match, "
    "hard_skill_gap) stay as short skill names (English technical terms OK).\n\n"
    "JOB-TYPE / REMOTE-OPTION FIT RULE: The candidate's preference includes "
    "a list of acceptable `job_type` values and a list of acceptable "
    "`remote_option` values. If a list is 'any' (or empty), treat it as no "
    "constraint. If a list is non-empty and the job posting's job_type is NOT "
    "in the candidate's list, significantly reduce the score and cap it at "
    "around 30. Apply the same penalty for a remote_option mismatch. If BOTH "
    "mismatch, cap the score even lower (around 15). When you apply this "
    "penalty, mention the mismatch briefly in the verdict (in Bahasa, 'kamu')."
)

RELEVANCE_SYSTEM_PROMPT = (
    "You screen a job posting for a candidate who lives in Indonesia. Answer "
    "each question independently.\n\n"
    "same_field: is the job plausibly in the same field as the candidate's "
    "preference title? false ONLY when clearly unrelated (e.g. software "
    "developer vs housekeeper, accountant vs truck driver). When in doubt, "
    "true. Ignore location for this question.\n\n"
    "residency_excludes_indonesia: true ONLY when the posting explicitly "
    "requires applicants to live or be based in specific countries/regions "
    "that do not include Indonesia (e.g. 'US only', 'must be based in the "
    "EU', 'Canada residents only', or an APPLICANT LOCATION RESTRICTION that "
    "names neither Indonesia nor a region containing it). These regions "
    "CONTAIN Indonesia: Worldwide, Anywhere, Global, Asia, Asia Pacific, "
    "APAC, Southeast Asia, SEA, ASEAN. false when any listed country or "
    "region contains Indonesia, when no location is given, and for timezone "
    "or working-hours requirements. An OFFICE LOCATION by itself is not a "
    "residency requirement.\n\n"
    "requires_foreign_work_authorization: true ONLY when the posting "
    "explicitly requires work authorization, right to work, citizenship or "
    "permanent residency in a country other than Indonesia, or says it does "
    "not sponsor visas.\n\n"
    "APPLICANT LOCATION RESTRICTION (remote jobs) lists where applicants "
    "must be based. OFFICE LOCATION is only where the office is.\n\n"
    "reason: a few words. When an answer rules the job out, name the cause "
    "and quote the real country or region (e.g. 'Canada residents only', "
    "'requires US work authorization', 'field mismatch: housekeeping')."
)

# ponytail: fixed cap — restriction clauses tend to sit at the end of a
# posting; 8000 chars covers every description seen so far (max ~7.3k) at
# ~2k tokens on the cheap model. Switch to head+tail if postings grow.
RELEVANCE_DESC_CHARS = 8000


def _candidate_context(profile) -> str:
    return "\n\n".join(filter(None, [profile.full_profile, profile.bio])) or "(empty)"


def _format_choices(values) -> str:
    return ", ".join(values) if values else "any"


def assess(job, preference) -> SkillAssessment:
    profile = preference.profile
    pref_job_types = _format_choices(preference.job_type)
    pref_remote_opts = _format_choices(preference.remote_option)
    user_msg = (
        f"CANDIDATE:\n{_candidate_context(profile)}\n\n"
        f"PREFERENCE: title={preference.title}, "
        f"job_type={pref_job_types}, remote_option={pref_remote_opts}\n\n"
        f"JOB TITLE: {job.title}\n"
        f"JOB COMPANY: {job.company}\n"
        f"JOB LOCATION: {job.location}\n"
        f"JOB JOB_TYPE: {job.job_type or 'unspecified'}\n"
        f"JOB REMOTE_OPTION: {job.remote_option or 'unspecified'}\n"
        f"JOB DESCRIPTION:\n{job.description}"
    )
    return get_prompt_manager().parse(
        system=SYSTEM_PROMPT,
        user=user_msg,
        response_format=SkillAssessment,
    )


def check_relevance(job, preference) -> RelevanceCheck:
    pref_job_types = _format_choices(preference.job_type)
    # Label the location in code so the model can't read an office address
    # as a residency rule (the cheap model got this wrong when left to infer).
    location_label = (
        "APPLICANT LOCATION RESTRICTION"
        if job.remote_option == RemoteOption.REMOTE
        else "OFFICE LOCATION"
    )
    user_msg = (
        f"PREFERENCE TITLE: {preference.title}\n"
        f"PREFERENCE JOB TYPE: {pref_job_types}\n\n"
        f"JOB TITLE: {job.title}\n"
        f"JOB COMPANY: {job.company}\n"
        f"JOB REMOTE_OPTION: {job.remote_option or 'unspecified'}\n"
        f"{location_label}: {job.location or 'unspecified'}\n"
        f"JOB DESCRIPTION:\n{(job.description or '')[:RELEVANCE_DESC_CHARS]}"
    )
    answer = get_prompt_manager().parse(
        system=RELEVANCE_SYSTEM_PROMPT,
        user=user_msg,
        response_format=_RelevanceAnswer,
        model=getattr(settings, "OPENAI_RELEVANCE_MODEL", "gpt-4o-mini"),
    )
    # An on-site/hybrid office abroad is fine (candidate may relocate), so a
    # residency flag only counts when the job isn't explicitly on-site/hybrid.
    office_bound = job.remote_option in (RemoteOption.ON_SITE, RemoteOption.HYBRID)
    blocked = answer.requires_foreign_work_authorization or (
        answer.residency_excludes_indonesia and not office_bound
    )
    return RelevanceCheck(
        is_relevant=answer.same_field and not blocked, reason=answer.reason
    )
