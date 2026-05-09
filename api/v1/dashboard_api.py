from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats(request):
    user = request.user
    today = timezone.localdate()
    thirty_days_ago = today - timedelta(days=29)

    assessments = Assessment.objects.filter(
        preference__profile__user=user, is_relevant=True
    )
    agg = assessments.aggregate(
        total=Count("id"),
        today=Count("id", filter=Q(created_on__date=today)),
        avg_score=Avg("score"),
        bucket_low=Count("id", filter=Q(score__lte=25)),
        bucket_mid_low=Count("id", filter=Q(score__gt=25, score__lte=50)),
        bucket_mid_high=Count("id", filter=Q(score__gt=50, score__lte=75)),
        bucket_high=Count("id", filter=Q(score__gt=75)),
    )
    by_status_rows = assessments.values("status").annotate(count=Count("id")).order_by()
    by_status = {row["status"]: row["count"] for row in by_status_rows}
    for value in AssessmentStatus.values:
        by_status.setdefault(value, 0)

    jobs_assessed = assessments.values("job_id").distinct().count()

    preferences = Preference.objects.filter(profile__user=user)
    pref_total = preferences.count()
    active_crawls = preferences.filter(status=PreferenceStatus.RUNNING).count()

    per_day_rows = (
        assessments.filter(created_on__date__gte=thirty_days_ago)
        .annotate(day=TruncDate("created_on"))
        .values("day")
        .annotate(count=Count("id"))
    )
    counts_by_date = {row["day"]: row["count"] for row in per_day_rows}
    trend = [
        {
            "date": (thirty_days_ago + timedelta(days=i)).isoformat(),
            "count": counts_by_date.get(thirty_days_ago + timedelta(days=i), 0),
        }
        for i in range(30)
    ]

    avg = agg["avg_score"]
    return Response(
        {
            "assessments": {
                "total": agg["total"],
                "today": agg["today"],
                "avg_score": round(avg, 1) if avg is not None else 0,
                "by_status": by_status,
            },
            "preferences": {
                "total": pref_total,
                "active_crawls": active_crawls,
            },
            "jobs_assessed": jobs_assessed,
            "score_buckets": [
                agg["bucket_low"] or 0,
                agg["bucket_mid_low"] or 0,
                agg["bucket_mid_high"] or 0,
                agg["bucket_high"] or 0,
            ],
            "trend_30d": trend,
        }
    )
