import json
from datetime import timedelta

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from assessment.models import Assessment
from jobs.models import Job
from profiles.models import Profile


class SuperuserRequiredMixin(View):
    @method_decorator(
        user_passes_test(lambda user: user.is_superuser, login_url="/login/")
    )
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class AdminLoginView(LoginView):
    template_name = "registration/login.html"
    success_url = "/dashboard/"


class DashboardView(SuperuserRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()
        cache_key = f"dashboard_stats_{today}_{request.GET.get('page', 1)}"
        cached = cache.get(cache_key)
        if cached:
            return render(request, "dashboard.html", cached)

        thirty_days_ago = today - timedelta(days=29)

        profile_stats = Profile.objects.aggregate(
            profile_count=Count("id"),
            profiles_today=Count("id", filter=Q(created_on__date=today)),
        )
        job_stats = Job.objects.aggregate(
            job_count=Count("id"),
            jobs_today=Count("id", filter=Q(created_on__date=today)),
        )
        jobs_by_type = list(
            Job.objects.values("job_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        jobs_by_remote = list(
            Job.objects.values("remote_option")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        assessment_stats = Assessment.objects.aggregate(
            assessment_count=Count("id"),
            assessments_today=Count("id", filter=Q(created_on__date=today)),
            avg_score=Avg("score"),
            bucket_low=Count("id", filter=Q(score__lte=25)),
            bucket_mid_low=Count("id", filter=Q(score__gt=25, score__lte=50)),
            bucket_mid_high=Count("id", filter=Q(score__gt=50, score__lte=75)),
            bucket_high=Count("id", filter=Q(score__gt=75)),
        )

        recent_qs = Assessment.objects.select_related("job", "profile").order_by(
            "-created_on"
        )
        paginator = Paginator(recent_qs, 10)
        recent_assessments = paginator.get_page(request.GET.get("page", 1))

        top_profiles = (
            Profile.objects.filter(assessments__created_on__date__gte=thirty_days_ago)
            .annotate(
                assessment_count=Count("assessments"),
                best_score=Max("assessments__score"),
            )
            .order_by("-best_score", "-assessment_count")[:10]
        )

        per_day = (
            Assessment.objects.filter(created_on__date__range=[thirty_days_ago, today])
            .extra({"date": "date(created_on)"})
            .values("date")
            .annotate(count=Count("id"))
        )
        counts = {row["date"]: row["count"] for row in per_day}
        date_range = [thirty_days_ago + timedelta(days=i) for i in range(30)]
        daily_assessments = [counts.get(str(d), counts.get(d, 0)) for d in date_range]
        date_labels = [d.strftime("%Y-%m-%d") for d in date_range]

        avg_score = assessment_stats["avg_score"]
        avg_score_display = round(avg_score, 1) if avg_score is not None else 0

        context = {
            **profile_stats,
            **job_stats,
            **assessment_stats,
            "avg_score_display": avg_score_display,
            "jobs_by_type": jobs_by_type,
            "jobs_by_remote": jobs_by_remote,
            "recent_assessments": recent_assessments,
            "top_profiles": top_profiles,
            "daily_assessments_json": json.dumps(daily_assessments),
            "date_labels_json": json.dumps(date_labels),
            "jobs_by_type_labels_json": json.dumps(
                [(j["job_type"] or "unspecified") for j in jobs_by_type]
            ),
            "jobs_by_type_counts_json": json.dumps([j["count"] for j in jobs_by_type]),
        }
        cache.set(cache_key, context, 300)
        return render(request, "dashboard.html", context)
