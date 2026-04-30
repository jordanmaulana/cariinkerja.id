from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from core.api.v1.serializers import (
    LoginSerializer,
    OnboardingSerializer,
    ProfileSerializer,
    SignupSerializer,
    UserSerializer,
)


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
