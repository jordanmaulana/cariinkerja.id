"""Job-title sanity check via Jev (TypeSafe AI's typed-decision model)."""

import logging
from functools import cache

from django.conf import settings
from typesafe_sdk import Choice, TypeSafeClient

logger = logging.getLogger(__name__)

VALID, INVALID, MULTIPLE = "valid", "invalid", "multiple"

# ponytail: fixed threshold; tune from the logged probabilities if users
# report false blocks.
MIN_BLOCK_PROBABILITY = 0.7

JOB_TITLE_QUESTION = Choice(
    instructions=(
        "A job seeker in Indonesia typed this into the 'job title' box of a job "
        "search app. The text may be Bahasa Indonesia or English. "
        "Is it one real job title?"
    ),
    # 'QA tester' sits under VALID on purpose so tester roles don't get pulled
    # toward the 'test'/'testes' placeholder examples under INVALID.
    criteria={
        VALID: (
            "Exactly one real job title, profession or role someone gets hired "
            "as, e.g. 'Sales manager', 'Guru bahasa Inggris', 'UI/UX designer', "
            "'QA tester', 'Kurir', 'Barista', 'HRD', 'Admin gudang'. Seniority "
            "words or a slash inside one role (UI/UX, Admin/Staff) still count "
            "as one role."
        ),
        MULTIPLE: (
            "Two or more different jobs at once, e.g. 'Sales manager, programmer', "
            "'Akuntan atau admin gudang', 'Desainer grafis dan content writer'."
        ),
        INVALID: (
            "Not a job title: gibberish or keyboard mashing, test or placeholder "
            "input ('test', 'testes', 'coba', 'qwerty'), a person's name, a "
            "company name, a sentence or question, or a random word that is not "
            "a profession, e.g. 'asdfgh', 'Budi', 'kerja apa aja', "
            "'tolong bantu saya'."
        ),
    },
)


@cache
def _client() -> TypeSafeClient:
    # One client per process; construction builds an HTTP client.
    return TypeSafeClient(api_key=settings.TYPESAFE_API_KEY)


def classify_job_title(title: str) -> str:
    """Return VALID, INVALID or MULTIPLE.

    Fails open (VALID) when Jev is unconfigured, errors, or isn't confident:
    a third-party hiccup must never block onboarding or a paid search.
    """
    if not settings.TYPESAFE_API_KEY:
        return VALID
    try:
        response = _client().system_one(
            state={"job_title": title},
            questions={"title": JOB_TITLE_QUESTION},
            timeout=5,
        )
        answer = response.choices["title"]
    except Exception:
        logger.warning("Jev job-title check failed; allowing %r", title, exc_info=True)
        return VALID
    probability = answer.probabilities.get(answer.choice, 0.0)
    logger.info("Jev job-title %r -> %s (p=%.2f)", title, answer.choice, probability)
    if answer.choice != VALID and probability < MIN_BLOCK_PROBABILITY:
        return VALID
    return answer.choice
