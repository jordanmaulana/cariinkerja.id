from __future__ import annotations

# Substring match, case-insensitive. Staffing/crowdwork brands to exclude.
BLOCKED_COMPANY_SUBSTRINGS = ("mindrift", "toloka")


def is_blocked_company(company: str | None) -> bool:
    if not company:
        return False
    name = company.lower()
    return any(s in name for s in BLOCKED_COMPANY_SUBSTRINGS)
