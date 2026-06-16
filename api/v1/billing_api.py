import time

from django.conf import settings as dj_settings
from django.db import transaction
from django.http import HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.v1.serializers import (
    CheckoutSerializer,
    PlanSerializer,
    SubscriptionSerializer,
)
from billing.models import Plan, Subscription, SubscriptionStatus, effective_price
from billing.upgrades import (
    UpgradeNotAllowed,
    compute_upgrade_quote,
    get_active_subscription,
)
from core.payments.mayar import (
    MayarError,
    PAID_STATUSES,
    create_payment_link,
    get_payment_status,
)
from core.payments.subscriptions import (
    activate_subscription,
    cancel_pending_subscription,
)
from core.realtime import _client as redis_client, user_channel
from core.tasks import (
    CHECKOUT_POLL_INTERVAL_SECONDS,
    poll_subscription_after_checkout,
)
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference

SSE_PING_SECONDS = 15


def _payment_gate(profile):
    if profile.linkedin_ingested_at and not profile.linkedin_quality_ok:
        return {
            "code": "linkedin_quality",
            "detail": profile.linkedin_quality_reason
            or "LinkedIn profile needs more detail before payment.",
        }
    waiting_admin = Preference.objects.filter(
        profile=profile, status=PreferenceStatus.WAITING_ADMIN
    ).exists()
    if waiting_admin:
        return {
            "code": "waiting_admin",
            "detail": "Sabar bentar ya.. Kami lagi ngumpulin loker di posisi yang kamu pilih.",
        }
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_gate(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    gate = _payment_gate(profile)
    if gate is None:
        return Response({"locked": False})
    return Response({"locked": True, **gate})


@api_view(["GET"])
@permission_classes([AllowAny])
def list(request):
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
def detail(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    base = Subscription.objects.filter(profile=profile).select_related("plan")
    sub = (
        base.filter(status=SubscriptionStatus.ACTIVE, expires_at__gt=timezone.now())
        .order_by("-created_on")
        .first()
        or base.filter(status=SubscriptionStatus.PENDING)
        .order_by("-created_on")
        .first()
        or base.filter(status=SubscriptionStatus.EXPIRED)
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
def create(request):
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

    gate = _payment_gate(profile)
    if gate is not None:
        return Response(
            {"locked": True, **gate},
            status=status.HTTP_409_CONFLICT,
        )

    active_sub = get_active_subscription(profile)
    is_upgrade = False
    if active_sub is not None and active_sub.plan_id != plan.id:
        if plan.price <= active_sub.plan.price:
            return Response(
                {
                    "detail": "Downgrade is not available.",
                    "code": "downgrade",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_upgrade = True

    with transaction.atomic():
        existing = (
            Subscription.objects.select_for_update()
            .filter(profile=profile, status=SubscriptionStatus.PENDING)
            .order_by("-created_on")
            .first()
        )
        if existing is not None:
            if existing.plan_id == plan.id:
                return Response(
                    {
                        "subscription_id": existing.id,
                        "payment_link": existing.payment_link,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {
                    "detail": "You already have a pending payment. Resume or cancel it first.",
                    "pending_subscription_id": existing.id,
                    "pending_plan_id": existing.plan_id,
                    "payment_link": existing.payment_link,
                },
                status=status.HTTP_409_CONFLICT,
            )
        if is_upgrade:
            try:
                quote = compute_upgrade_quote(profile, plan, current_sub=active_sub)
            except UpgradeNotAllowed as exc:
                return Response(
                    {"detail": exc.detail, "code": exc.code},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sub = Subscription.objects.create(
                profile=profile,
                plan=plan,
                status=SubscriptionStatus.PENDING,
                payment_provider="mayar",
                replaces=active_sub,
            )
            amount = quote["charge"]
            description = (
                f"Upgrade {active_sub.plan.name}→{plan.name} "
                f"(+{quote['bonus_days']:.1f}d bonus)"
            )
        else:
            sub = Subscription.objects.create(
                profile=profile,
                plan=plan,
                status=SubscriptionStatus.PENDING,
                payment_provider="mayar",
            )
            amount = effective_price(plan, profile)
            description = f"{plan.name} subscription (1 month)"
            if amount < plan.price:
                description += " (Open-to-Work discount)"

    redirect_url = dj_settings.PAYMENT_REDIRECT_URL
    try:
        link = create_payment_link(
            name=profile.full_name or request.user.email,
            amount=amount,
            email=request.user.email,
            description=description,
            redirect_url=redirect_url,
            mobile=profile.phone or "",
        )
    except MayarError as exc:
        sub.delete()
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

    sub.payment_link = link["link"]
    sub.payment_ref = link["transaction_id"]
    sub.amount_paid = amount
    sub.save(
        update_fields=[
            "payment_link",
            "payment_ref",
            "amount_paid",
            "updated_on",
        ]
    )

    poll_subscription_after_checkout.apply_async(
        args=[sub.id], countdown=CHECKOUT_POLL_INTERVAL_SECONDS
    )

    return Response(
        {
            "subscription_id": sub.id,
            "payment_link": sub.payment_link,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def upgrade_quote(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    plan_id = request.query_params.get("plan_id")
    if not plan_id:
        return Response(
            {"detail": "plan_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    plan = get_object_or_404(Plan, pk=plan_id, is_active=True)
    try:
        quote = compute_upgrade_quote(profile, plan)
    except UpgradeNotAllowed as exc:
        return Response(
            {"detail": exc.detail, "code": exc.code},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(quote)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_pending(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    with transaction.atomic():
        sub = (
            Subscription.objects.select_for_update()
            .filter(profile=profile, status=SubscriptionStatus.PENDING)
            .order_by("-created_on")
            .first()
        )
        if sub is None:
            return Response(
                {"detail": "No pending subscription."},
                status=status.HTTP_404_NOT_FOUND,
            )
        cancel_pending_subscription(sub)
    return Response({"subscription_id": sub.id}, status=status.HTTP_200_OK)


def stream(request):
    """SSE stream of user-scoped events (token via ?token=... query param).

    EventSource cannot send custom headers, so we authenticate via the
    DRF auth token in the query string. Each open connection holds a
    sync worker — fine for the small expected concurrency on the plans
    page, revisit (gthread/async) before scaling.
    """
    token_key = request.GET.get("token") or ""
    try:
        token = Token.objects.select_related("user").get(key=token_key)
    except Token.DoesNotExist:
        return HttpResponseForbidden("invalid token")
    user = token.user

    def event_gen():
        pubsub = redis_client().pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(user_channel(user.id))
        try:
            yield ": connected\n\n"
            last_ping = time.monotonic()
            while True:
                msg = pubsub.get_message(timeout=1.0)
                if msg and msg.get("type") == "message":
                    data = msg["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"data: {data}\n\n"
                if time.monotonic() - last_ping > SSE_PING_SECONDS:
                    yield ": ping\n\n"
                    last_ping = time.monotonic()
        finally:
            pubsub.close()

    resp = StreamingHttpResponse(event_gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def recheck(request, pk):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    sub = get_object_or_404(
        Subscription.objects.select_related("plan"), pk=pk, profile=profile
    )
    if sub.status == SubscriptionStatus.ACTIVE:
        return Response(SubscriptionSerializer(sub).data)
    if sub.status != SubscriptionStatus.PENDING or not sub.payment_ref:
        return Response(
            {"detail": "Subscription is not pending payment."},
            status=status.HTTP_409_CONFLICT,
        )
    try:
        result = get_payment_status(sub.payment_ref)
    except MayarError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    if result["status"] in PAID_STATUSES:
        activate_subscription(sub)
    return Response(SubscriptionSerializer(sub).data)
