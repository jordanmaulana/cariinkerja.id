from django.db import models

from core.models import BaseModel


# Create your models here.
class Profile(BaseModel):
    user = models.OneToOneField(
        "auth.User", on_delete=models.CASCADE, related_name="profile"
    )
    full_name = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)

    class Meta:
        app_label = "profiles"
