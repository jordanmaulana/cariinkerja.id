from django.db import models


class Status(models.TextChoices):
    WAITING_PAYMENT = "waiting_payment", "Waiting Payment"
    WAITING_ADMIN = "waiting_admin", "Waiting Admin"
    RUNNING = "running", "Running"
    EXPIRED = "expired", "Expired"


class Source(models.TextChoices):
    JOBSTREET = "jobstreet", "JobStreet"
    INDEED = "indeed", "Indeed"
    LINKEDIN = "linkedin", "LinkedIn"
    DEALLS = "dealls", "Dealls"
