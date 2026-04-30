from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        email = kwargs.get("email") or username
        if not email or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
