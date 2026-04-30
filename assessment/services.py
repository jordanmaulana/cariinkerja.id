from django.conf import settings
from openai import OpenAI
from pydantic import BaseModel, Field


class SkillAssessment(BaseModel):
    soft_skill_match: list[str]
    soft_skill_gap: list[str]
    hard_skill_match: list[str]
    hard_skill_gap: list[str]
    score: int = Field(ge=0, le=100)
    verdict: str


SYSTEM_PROMPT = (
    "You assess candidate fit for a job posting. "
    "Return matched and missing soft & hard skills, a 0-100 score, "
    "and a short verdict (1-3 sentences) explaining the score."
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
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.parse(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format=SkillAssessment,
    )
    return resp.choices[0].message.parsed
