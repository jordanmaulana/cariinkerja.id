from django.db import models


class Status(models.TextChoices):
    WAITING = "waiting", "Waiting"
    RUNNING = "running", "Running"
    EXPIRED = "expired", "Expired"