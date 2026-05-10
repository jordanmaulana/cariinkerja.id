from django.conf import settings
from pydantic import BaseModel, Field

from core.openai import get_prompt_manager


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
    "Decide if a job posting is plausibly in the same field as the candidate's "
    "preference. Return is_relevant=false ONLY when the fields are clearly "
    "unrelated (e.g. software developer vs housekeeper, accountant vs truck "
    "driver). When in doubt, return true — borderline fits go to the full "
    "scorer downstream."
)


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
    user_msg = (
        f"PREFERENCE TITLE: {preference.title}\n"
        f"PREFERENCE JOB TYPE: {pref_job_types}\n\n"
        f"JOB TITLE: {job.title}\n"
        f"JOB COMPANY: {job.company}\n"
        f"JOB DESCRIPTION (first 1500 chars):\n{(job.description or '')[:1500]}"
    )
    return get_prompt_manager().parse(
        system=RELEVANCE_SYSTEM_PROMPT,
        user=user_msg,
        response_format=RelevanceCheck,
        model=getattr(settings, "OPENAI_RELEVANCE_MODEL", "gpt-4o-mini"),
    )
