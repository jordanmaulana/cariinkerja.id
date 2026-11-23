from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1.serializers import (
    OnboardingSerializer,
    ProfileCvSerializer,
    ProfileSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail(request):
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cv(request):
    """Edit the CV text (or re-upload the PDF); the AI re-reads it in the background."""
    profile = getattr(request.user, "profile", None)
    if profile is None:
        return Response(
            {"detail": "Profile missing for user."},
            status=status.HTTP_404_NOT_FOUND,
        )
    if profile.linkedin_url:
        return Response(
            {"detail": "Profilmu pakai LinkedIn, jadi nggak ada CV yang bisa diubah."},
            status=status.HTTP_409_CONFLICT,
        )
    next_at = profile.cv_next_edit_at
    if next_at:
        # ponytail: check-then-save, so two simultaneous requests can both pass
        # (worst case one extra LLM call); use a conditional UPDATE if that matters.
        when = timezone.localtime(next_at).strftime("%d/%m/%Y %H.%M")
        return Response(
            {
                "detail": "CV cuma bisa diubah sekali sehari. Kamu bisa ubah "
                f"lagi mulai {when} WIB.",
                "next_edit_at": next_at,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    serializer = ProfileCvSerializer(data=request.data, context={"profile": profile})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(ProfileSerializer(profile).data)
