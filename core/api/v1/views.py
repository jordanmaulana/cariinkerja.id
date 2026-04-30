from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from assessment.consts import Status as AssessmentStatus
from assessment.models import Assessment
from core.api.v1.serializers import (
    AssessmentSerializer,
    AssessmentStatusUpdateSerializer,
    LoginSerializer,
    OnboardingSerializer,
    PreferenceSerializer,
    ProfileSerializer,
    SignupSerializer,
    UserSerializer,
)
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    serializer = SignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token = serializer.context["token"]
    return Response(
        {"token": token.key, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data["user"]
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_me(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(ProfileSerializer(profile).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def onboarding(request):
    serializer = OnboardingSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    profile = serializer.save()
    return Response(ProfileSerializer(profile).data)


def _user_assessments(user):
    return Assessment.objects.filter(preference__profile__user=user).select_related(
        "job", "preference"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assessment_list(request):
    qs = _user_assessments(request.user).order_by("-created_on")
    status_param = request.query_params.get("status")
    if status_param:
        if status_param not in AssessmentStatus.values:
            return Response(
                {"detail": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST
            )
        qs = qs.filter(status=status_param)
    min_score_param = request.query_params.get("min_score")
    if min_score_param:
        try:
            min_score = int(min_score_param)
        except ValueError:
            return Response(
                {"detail": "Invalid min_score."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = qs.filter(score__gte=min_score)
    return Response(AssessmentSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    user = request.user
    today = timezone.localdate()
    thirty_days_ago = today - timedelta(days=29)

    assessments = Assessment.objects.filter(preference__profile__user=user)
    agg = assessments.aggregate(
        total=Count("id"),
        today=Count("id", filter=Q(created_on__date=today)),
        avg_score=Avg("score"),
        bucket_low=Count("id", filter=Q(score__lte=25)),
        bucket_mid_low=Count("id", filter=Q(score__gt=25, score__lte=50)),
        bucket_mid_high=Count("id", filter=Q(score__gt=50, score__lte=75)),
        bucket_high=Count("id", filter=Q(score__gt=75)),
    )
    by_status_rows = (
        assessments.values("status").annotate(count=Count("id")).order_by()
    )
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


def _user_preferences(user):
    return Preference.objects.filter(profile__user=user).order_by("-created_on")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def preference_list(request):
    if request.method == "GET":
        qs = _user_preferences(request.user)
        return Response(PreferenceSerializer(qs, many=True).data)
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = PreferenceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pref = serializer.save(profile=profile)
    return Response(
        PreferenceSerializer(pref).data, status=status.HTTP_201_CREATED
    )


@api_view(["GET", "PATCH", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def preference_detail(request, pk):
    pref = get_object_or_404(_user_preferences(request.user), pk=pk)
    if request.method == "GET":
        return Response(PreferenceSerializer(pref).data)
    if request.method == "DELETE":
        pref.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = PreferenceSerializer(
        pref, data=request.data, partial=request.method == "PATCH"
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def assessment_detail(request, pk):
    assessment = get_object_or_404(_user_assessments(request.user), pk=pk)
    if request.method == "GET":
        return Response(AssessmentSerializer(assessment).data)
    serializer = AssessmentStatusUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        assessment.status = serializer.validated_data["status"]
        assessment.save(update_fields=["status", "updated_on"])
    return Response(AssessmentSerializer(assessment).data)
