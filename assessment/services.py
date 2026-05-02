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
    "and a short verdict (1-3 sentences) explaining the score."
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


def assess(job, preference) -> SkillAssessment:
    profile = preference.profile
    user_msg = (
        f"CANDIDATE:\n{_candidate_context(profile)}\n\n"
        f"PREFERENCE: title={preference.title}, "
        f"job_type={preference.job_type}, remote_option={preference.remote_option}\n\n"
        f"JOB TITLE: {job.title}\n"
        f"JOB COMPANY: {job.company}\n"
        f"JOB LOCATION: {job.location}\n"
        f"JOB DESCRIPTION:\n{job.description}"
    )
    return get_prompt_manager().parse(
        system=SYSTEM_PROMPT,
        user=user_msg,
        response_format=SkillAssessment,
    )


def check_relevance(job, preference) -> RelevanceCheck:
    user_msg = (
        f"PREFERENCE TITLE: {preference.title}\n"
        f"PREFERENCE JOB TYPE: {preference.job_type}\n\n"
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
