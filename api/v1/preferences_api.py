from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1.serializers import PreferenceSerializer
from billing.upgrades import get_active_subscription
from profiles.consts import Status as PreferenceStatus
from profiles.models import Preference


def _user_preferences(user):
    return Preference.objects.filter(profile__user=user).order_by("-created_on")


def list(request):
    qs = _user_preferences(request.user)
    return Response(PreferenceSerializer(qs, many=True).data)


def create(request):
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if not profile.whitelist:
        active_sub = get_active_subscription(profile)
        if active_sub is None:
            return Response(
                {"detail": "Active subscription required to create a finder."},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        used = Preference.objects.filter(profile=profile).count()
        if used >= active_sub.plan.preference_limit:
            return Response(
                {"detail": "Preference limit reached for current plan."},
                status=status.HTTP_409_CONFLICT,
            )
    serializer = PreferenceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pref = serializer.save(profile=profile)
    return Response(PreferenceSerializer(pref).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def list_or_create(request):
    if request.method == "POST":
        return create(request)
    return list(request)


@api_view(["GET", "PATCH", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def detail(request, pk):
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
