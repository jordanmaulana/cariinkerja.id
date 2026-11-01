from __future__ import annotations

import re

# Substring match, case-insensitive. Staffing/crowdwork brands to exclude.
BLOCKED_COMPANY_SUBSTRINGS = ("mindrift", "toloka")


def is_blocked_company(company: str | None) -> bool:
    if not company:
        return False
    name = company.lower()
    return any(s in name for s in BLOCKED_COMPANY_SUBSTRINGS)


def title_words(query: str | None) -> list[str]:
    """Lowercase words of a title search, dropping one-letter fragments."""
    return [w for w in re.split(r"\W+", (query or "").lower()) if len(w) > 1]


def _stem(word: str) -> str:
    """Drop adjective -al / plural -s so "operational" matches "Operations"."""
    if word.endswith("al") and word[:-2].endswith(("ion", "ic")):
        return word[:-2]  # operational -> operation, logistical -> logistic
    if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]  # logistics -> logistic; "ios"/"aws" untouched
    return word


def title_has_words(title: str, words: list[str]) -> bool:
    """Every query word (stemmed) appears in the title, case-insensitive.

    ponytail: suffix stripping only, no synonyms ("Mobile Developer" misses
    "Flutter Engineer"). Loosen if recall is poor.
    """
    t = title.lower()
    return all(_stem(w) in t for w in words)
