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
