from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.views import SuperuserRequiredMixin
from profiles.models import Profile


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
        return get_object_or_404(Profile.objects.prefetch_related("preferences"), pk=pk)

    def _render(self, request, profile):
        return render(
            request,
            "profiles/detail.html",
            {
                "profile": profile,
                "preferences": profile.preferences.all().order_by("-created_on"),
            },
        )

    def get(self, request, pk):
        return self._render(request, self._get(pk))

    def post(self, request, pk):
        profile = self._get(pk)
        full_name = request.POST.get("full_name", "").strip()
        linkedin_url = request.POST.get("linkedin_url", "").strip()
        bio = request.POST.get("bio", "").strip()
        full_profile = request.POST.get("full_profile", "").strip()

        if linkedin_url:
            try:
                URLValidator()(linkedin_url)
            except ValidationError:
                messages.error(request, "Invalid LinkedIn URL.")
                return self._render(request, profile)

        with transaction.atomic():
            profile.full_name = full_name or None
            profile.linkedin_url = linkedin_url or None
            profile.bio = bio or None
            profile.full_profile = full_profile or None
            profile.save(
                update_fields=[
                    "full_name",
                    "linkedin_url",
                    "bio",
                    "full_profile",
                    "updated_on",
                ]
            )

        messages.success(request, "Profile updated.")
        return redirect("profile_detail", pk=profile.pk)
