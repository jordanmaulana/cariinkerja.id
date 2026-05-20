from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from assessment.models import Assessment
from jobs.models import Job
from profiles.models import Profile

CACHE_KEY = "landing:public_stats:v1"
CACHE_TTL = 60


@api_view(["GET"])
@permission_classes([AllowAny])
def public_stats(request):
    payload = cache.get(CACHE_KEY)
    if payload is None:
        today = timezone.localdate()
        profiles = Profile.objects.aggregate(
            total=Count("id"),
            today=Count("id", filter=Q(created_on__date=today)),
        )
        jobs = Job.objects.aggregate(
            total=Count("id"),
            today=Count("id", filter=Q(created_on__date=today)),
        )
        assessments = Assessment.objects.aggregate(
            total=Count("id"),
            today=Count("id", filter=Q(created_on__date=today)),
        )
        highly = Assessment.objects.aggregate(
            total=Count("id", filter=Q(score__gte=80)),
            today=Count("id", filter=Q(score__gte=80, created_on__date=today)),
        )
        payload = {
            "profiles": profiles,
            "jobs": jobs,
            "assessments": assessments,
            "highly_suitable": highly,
        }
        cache.set(CACHE_KEY, payload, CACHE_TTL)
    return Response(payload)
