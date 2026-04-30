from django.db import models


class Status(models.TextChoices):
    NEW = "new", "New"
    SEEN = "seen", "Seen"
    APPLIED = "applied", "Applied"
    REJECTED = "rejected", "Rejected"
    ACCEPTED = "accepted", "Accepted"
    