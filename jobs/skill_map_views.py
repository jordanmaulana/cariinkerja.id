"""Public Skill Map pages. Served on cariinkerja.id/skill/ via the reverse
proxy, so every absolute link is built from FRONTEND_URL."""

from __future__ import annotations

from datetime import date

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from billing.models import Plan
from jobs.models import SkillMapPage
from jobs.skill_map import format_date_id, visible_pages, visible_snapshot

CACHE_SECONDS = 60 * 60


def _base_context() -> dict:
    plan = Plan.objects.filter(is_active=True).order_by("price").first()
    return {"frontend_url": settings.FRONTEND_URL, "cheapest_plan": plan}


def _dates(data: dict) -> dict:
    return {
        "window_start": format_date_id(date.fromisoformat(data["window_start"])),
        "window_end": format_date_id(date.fromisoformat(data["window_end"])),
    }


@cache_page(CACHE_SECONDS)
def skill_map_index(request):
    pages = [
        {"page": page, "snap": snap, "top": snap.data.get("hard_skills", [])[:3]}
        for page, snap in visible_pages()
    ]
    updated = max((p["snap"].computed_on for p in pages), default=None)
    ctx = _base_context() | {
        "pages": pages,
        "updated": format_date_id(updated) if updated else None,
        "canonical": f"{settings.FRONTEND_URL}/skill/",
    }
    return render(request, "skillmap/index.html", ctx)


@cache_page(CACHE_SECONDS)
def skill_map_detail(request, slug: str):
    page = get_object_or_404(SkillMapPage, slug=slug)
    snap = visible_snapshot(page)
    if snap is None:
        raise Http404("Skill Map page not available")
    related = [p for p, _ in visible_pages() if p.pk != page.pk][:8]
    ctx = _base_context() | {
        "page": page,
        "snap": snap,
        "data": snap.data,
        "related": related,
        "canonical": f"{settings.FRONTEND_URL}/skill/{page.slug}/",
        **_dates(snap.data),
    }
    return render(request, "skillmap/detail.html", ctx)


@cache_page(CACHE_SECONDS)
def skill_map_sitemap(request):
    ctx = {"frontend_url": settings.FRONTEND_URL, "pages": visible_pages()}
    return render(request, "skillmap/sitemap.xml", ctx, content_type="application/xml")
