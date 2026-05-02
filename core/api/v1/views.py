from datetime import timedelta

from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, Paginator
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
    CheckoutSerializer,
    GoogleAuthSerializer,
    OnboardingSerializer,
    PlanSerializer,
    PreferenceSerializer,
    ProfileSerializer,
    SubscriptionSerializer,
    UserSerializer,
)
from core.models import Plan, Subscription, SubscriptionStatus, effective_price
from core.payments.mayar import MayarError, create_payment_link, verify_webhook
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference, Profile

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def google_auth(request):
    serializer = GoogleAuthSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    claims = serializer.validated_data["claims"]
    email = claims["email"].lower()
    google_name = (claims.get("name") or "").strip()
    with transaction.atomic():
        user = User.objects.filter(email__iexact=email).first()
        created = False
        if user is None:
            user = User.objects.create_user(username=email, email=email)
            created = True
        profile, _ = Profile.objects.get_or_create(user=user)
        if (
            google_name
            and not profile.full_name
            and profile.suggested_full_name != google_name
        ):
            profile.suggested_full_name = google_name
            profile.save()
        token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {"token": token.key, "user": UserSerializer(user).data},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


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
    return Assessment.objects.filter(
        preference__profile__user=user, is_relevant=True
    ).select_related("job", "preference")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def assessment_list(request):
    qs = _user_assessments(request.user).order_by("-created_on")
    status_values = request.query_params.getlist("status")
    if status_values:
        for value in status_values:
            if value not in AssessmentStatus.values:
                return Response(
                    {"detail": "Invalid status."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        qs = qs.filter(status__in=status_values)
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

    try:
        page = int(request.query_params.get("page", 1))
    except ValueError:
        return Response({"detail": "Invalid page."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        page_size = int(request.query_params.get("page_size", 25))
    except ValueError:
        return Response(
            {"detail": "Invalid page_size."}, status=status.HTTP_400_BAD_REQUEST
        )
    page = max(page, 1)
    page_size = max(1, min(page_size, 100))

    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page)
        results = AssessmentSerializer(page_obj.object_list, many=True).data
    except EmptyPage:
        results = []

    return Response(
        {
            "count": paginator.count,
            "page": page,
            "page_size": page_size,
            "num_pages": paginator.num_pages,
            "results": results,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
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
    return Response(PreferenceSerializer(pref).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def preference_detail(request, pk):
    pref = get_object_or_404(_user_preferences(request.user), pk=pk)
    if request.method == "GET":
        return Response(PreferenceSerializer(pref).data)
    if request.method == "DELETE":
        if pref.status != PreferenceStatus.WAITING_PAYMENT:
            return Response(
                {"detail": "Finder cannot be deleted after submission."},
                status=status.HTTP_409_CONFLICT,
            )
        pref.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    was_running = pref.status == PreferenceStatus.RUNNING
    serializer = PreferenceSerializer(
        pref, data=request.data, partial=request.method == "PATCH"
    )
    serializer.is_valid(raise_exception=True)
    pref = serializer.save()
    if was_running:
        pref.status = PreferenceStatus.WAITING_ADMIN
        pref.save(update_fields=["status", "updated_on"])
    return Response(PreferenceSerializer(pref).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def plan_list(request):
    qs = Plan.objects.filter(is_active=True).order_by("price")
    cheapest_id = qs.values_list("id", flat=True).first()
    serializer = PlanSerializer(
        qs,
        many=True,
        context={"request": request, "cheapest_plan_id": cheapest_id},
    )
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_subscription(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    sub = (
        Subscription.objects.filter(profile=profile)
        .select_related("plan")
        .order_by("-created_on")
        .first()
    )
    if sub is None:
        return Response(
            {"detail": "No subscription."}, status=status.HTTP_404_NOT_FOUND
        )
    return Response(SubscriptionSerializer(sub).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = CheckoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    plan = get_object_or_404(
        Plan, pk=serializer.validated_data["plan_id"], is_active=True
    )

    with transaction.atomic():
        sub = Subscription.objects.create(
            profile=profile,
            plan=plan,
            status=SubscriptionStatus.PENDING,
            payment_provider="mayar",
        )

    redirect_url = dj_settings.PAYMENT_REDIRECT_URL
    amount = effective_price(plan, profile)
    description = f"{plan.name} subscription (1 month)"
    if amount < plan.price:
        description += " (Open-to-Work discount)"
    try:
        link = create_payment_link(
            name=profile.full_name or request.user.email,
            amount=amount,
            email=request.user.email,
            description=description,
            redirect_url=redirect_url,
        )
    except MayarError as exc:
        sub.delete()
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    sub.payment_link = link["link"]
    sub.payment_ref = link["transaction_id"]
    sub.save(update_fields=["payment_link", "payment_ref", "updated_on"])

    return Response(
        {
            "subscription_id": sub.id,
            "payment_link": sub.payment_link,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def mayar_webhook(request):
    if not verify_webhook(request):
        return Response(
            {"detail": "Invalid token."}, status=status.HTTP_401_UNAUTHORIZED
        )
    event = request.data.get("event") or ""
    data = request.data.get("data") or {}
    payment_ref = str(data.get("id") or data.get("transaction_id") or "")
    if not payment_ref:
        return Response(
            {"detail": "Missing transaction id."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    sub = Subscription.objects.filter(payment_ref=payment_ref).first()
    if sub is None:
        return Response(
            {"detail": "Subscription not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if event in {"payment.received", "payment.success", "PAYMENT_RECEIVED"}:
        if sub.status != SubscriptionStatus.ACTIVE:
            now = timezone.now()
            sub.status = SubscriptionStatus.ACTIVE
            sub.started_at = now
            sub.expires_at = now + timedelta(days=30)
            sub.save(
                update_fields=[
                    "status",
                    "started_at",
                    "expires_at",
                    "updated_on",
                ]
            )
    elif event in {"payment.failed", "payment.expired"}:
        if sub.status == SubscriptionStatus.PENDING:
            sub.status = SubscriptionStatus.CANCELLED
            sub.save(update_fields=["status", "updated_on"])

    return Response({"ok": True})


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
