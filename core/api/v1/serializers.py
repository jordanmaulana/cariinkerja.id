from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from jobs.consts import JobType, RemoteOption
from profiles.models import Preference, Profile

User = get_user_model()


class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        with transaction.atomic():
            user = User.objects.create_user(
                username=email, email=email, password=validated_data["password"]
            )
            Profile.objects.create(user=user)
            token, _ = Token.objects.get_or_create(user=user)
        self.context["token"] = token
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")
        user = authenticate(request, email=attrs["email"], password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    onboarded = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "onboarded"]

    def _profile(self, user):
        return getattr(user, "profile", None)

    def get_full_name(self, user):
        profile = self._profile(user)
        return profile.full_name if profile else None

    def get_onboarded(self, user):
        profile = self._profile(user)
        return bool(profile and profile.full_name)


class ProfileSerializer(serializers.ModelSerializer):
    onboarded = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ["full_name", "linkedin_url", "bio", "onboarded"]

    def get_onboarded(self, profile):
        return bool(profile.full_name)


class OnboardingSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(max_length=255)
    job_type = serializers.ChoiceField(choices=JobType.choices)
    remote_option = serializers.ChoiceField(choices=RemoteOption.choices)

    def save(self, **kwargs):
        user = self.context["request"].user
        data = self.validated_data
        with transaction.atomic():
            profile = user.profile
            profile.full_name = data["full_name"]
            profile.linkedin_url = data.get("linkedin_url") or None
            profile.bio = data.get("bio") or None
            profile.save()
            Preference.objects.create(
                profile=profile,
                title=data["title"],
                job_type=data["job_type"],
                remote_option=data["remote_option"],
            )
        return profile
