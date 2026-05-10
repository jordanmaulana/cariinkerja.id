from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1.serializers import OnboardingSerializer, ProfileSerializer


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
