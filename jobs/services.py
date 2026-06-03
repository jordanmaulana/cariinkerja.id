from django.conf import settings
from pydantic import BaseModel

from core.openai import get_prompt_manager


class JobSkills(BaseModel):
    hard_skills: list[str]
    soft_skills: list[str]


SYSTEM_PROMPT = (
    "Extract the skills a job posting REQUIRES from its description. "
    "Return two short lists: hard_skills (concrete, technical/tool/domain skills, "
    "e.g. 'Python', 'financial modeling') and soft_skills (interpersonal/behavioral, "
    "e.g. 'communication', 'teamwork'). Use short skill names (English technical "
    "terms OK). Only include skills actually stated or clearly implied; do not invent. "
    "Return empty lists if none are identifiable."
)


def extract_skills(job) -> JobSkills:
    user_msg = (
        f"JOB TITLE: {job.title}\n"
        f"COMPANY: {job.company}\n"
        f"DESCRIPTION:\n{job.description or ''}"
    )
    return get_prompt_manager().parse(
        system=SYSTEM_PROMPT,
        user=user_msg,
        response_format=JobSkills,
        model=getattr(settings, "OPENAI_RELEVANCE_MODEL", "gpt-4o-mini"),
    )
