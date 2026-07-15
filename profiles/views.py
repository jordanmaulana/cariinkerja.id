from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from core.views import SuperuserRequiredMixin
from profiles.models import Profile
from profiles.services import ingest_linkedin
from profiles.tasks import crawl_linkedin_for_profile


class ProfileListView(SuperuserRequiredMixin, View):
    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = Profile.objects.annotate(preference_count=Count("preferences")).order_by(
            "-created_on"
        )
        if q:
            qs = qs.filter(full_name__icontains=q)

        paginator = Paginator(qs, 20)
        profiles = paginator.get_page(request.GET.get("page", 1))
        total_count = Profile.objects.count()

        context = {
            "profiles": profiles,
            "q": q,
            "total_count": total_count,
        }
        return render(request, "profiles/list.html", context)


class ProfileDetailView(SuperuserRequiredMixin, View):
    def _get(self, pk):
        return get_object_or_404(Profile, pk=pk)

    def _render(self, request, profile):
        return render(
            request,
            "profiles/detail.html",
            {
                "profile": profile,
                "preferences": profile.preferences.order_by("-created_on"),
            },
        )

    def get(self, request, pk):
        return self._render(request, self._get(pk))

    def post(self, request, pk):
        profile = self._get(pk)
        full_name = request.POST.get("full_name", "").strip()
        linkedin_url = request.POST.get("linkedin_url", "").strip()
        bio = request.POST.get("bio", "").strip()
        linkedin_raw = request.POST.get("linkedin_raw", "").strip()
        full_profile = request.POST.get("full_profile", "").strip()
        override = request.POST.get("manual_full_profile_override") == "1"

        if linkedin_url:
            try:
                URLValidator()(linkedin_url)
            except ValidationError:
                messages.error(request, "Invalid LinkedIn URL.")
                return self._render(request, profile)

        update_fields = ["full_name", "linkedin_url", "bio", "updated_on"]
        profile.full_name = full_name or None
        profile.linkedin_url = linkedin_url or None
        profile.bio = bio or None

        run_ingest = (
            not override
            and linkedin_raw
            and linkedin_raw != (profile.linkedin_raw or "")
        )

        if run_ingest:
            try:
                result = ingest_linkedin(linkedin_raw)
            except Exception as exc:
                messages.error(request, f"LinkedIn ingest failed: {exc}")
                profile.linkedin_raw = linkedin_raw
                profile.save(update_fields=update_fields + ["linkedin_raw"])
                return self._render(request, profile)
            profile.linkedin_raw = linkedin_raw
            profile.full_profile = result.cleaned_full_profile or None
            profile.open_to_work = result.open_to_work
            profile.linkedin_quality_ok = not result.is_sparse
            profile.linkedin_quality_reason = (
                result.sparse_reason or result.quality_notes or ""
            )
            profile.linkedin_ingested_at = timezone.now()
            update_fields += [
                "linkedin_raw",
                "full_profile",
                "open_to_work",
                "linkedin_quality_ok",
                "linkedin_quality_reason",
                "linkedin_ingested_at",
            ]
        else:
            if override:
                profile.full_profile = full_profile or None
                update_fields.append("full_profile")
            if linkedin_raw and linkedin_raw != (profile.linkedin_raw or ""):
                profile.linkedin_raw = linkedin_raw
                update_fields.append("linkedin_raw")

            new_open_to_work = request.POST.get("open_to_work") == "1"
            if new_open_to_work != profile.open_to_work:
                profile.open_to_work = new_open_to_work
                update_fields.append("open_to_work")

        with transaction.atomic():
            profile.save(update_fields=update_fields)

        messages.success(request, "Profile updated.")
        return redirect("profile_detail", pk=profile.pk)


class ProfileReingestLinkedinView(SuperuserRequiredMixin, View):
    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        if not profile.linkedin_url:
            messages.error(request, "Profile has no LinkedIn URL.")
        else:
            crawl_linkedin_for_profile.delay(profile.id)
            messages.success(request, "LinkedIn re-ingest queued.")
        return redirect("profile_detail", pk=profile.pk)


class ProfileRegenerateFullProfileView(SuperuserRequiredMixin, View):
    """Re-run the LLM against the stored linkedin_raw. No Apify, no crawl.

    ProfileDetailView.post only runs the ingest when the pasted raw *differs*
    from what is stored, so re-submitting the same paste is a no-op. This is
    the escape hatch for that. linkedin_raw is read-only here.
    """

    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        if not profile.linkedin_raw:
            messages.error(request, "No LinkedIn raw paste to regenerate from.")
            return redirect("profile_detail", pk=profile.pk)

        try:
            result = ingest_linkedin(profile.linkedin_raw)
        except Exception as exc:
            messages.error(request, f"Regenerate failed: {exc}")
            return redirect("profile_detail", pk=profile.pk)

        profile.full_profile = result.cleaned_full_profile or None
        profile.open_to_work = result.open_to_work
        profile.linkedin_quality_ok = not result.is_sparse
        profile.linkedin_quality_reason = (
            result.sparse_reason or result.quality_notes or ""
        )
        profile.linkedin_ingested_at = timezone.now()
        with transaction.atomic():
            profile.save(
                update_fields=[
                    "full_profile",
                    "open_to_work",
                    "linkedin_quality_ok",
                    "linkedin_quality_reason",
                    "linkedin_ingested_at",
                    "updated_on",
                ]
            )

        messages.success(request, "Full profile regenerated from stored raw.")
        return redirect("profile_detail", pk=profile.pk)
