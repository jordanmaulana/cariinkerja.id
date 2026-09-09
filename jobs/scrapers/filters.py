from __future__ import annotations

# Substring match, case-insensitive. Staffing/crowdwork brands to exclude.
# "misi seru" is KitaLulus's own reward-microtask brand (WhatsApp-group tasks
# paying a one-off reward), not employment. Note it must stay this specific:
# bare "KitaLulus" postings are that company's genuine hiring.
BLOCKED_COMPANY_SUBSTRINGS = ("mindrift", "toloka", "misi seru")


def is_blocked_company(company: str | None) -> bool:
    if not company:
        return False
    name = company.lower()
    return any(s in name for s in BLOCKED_COMPANY_SUBSTRINGS)
