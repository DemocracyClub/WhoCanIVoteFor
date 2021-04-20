from django.db import models

from django_extensions.db.models import TimeStampedModel

FOUND_USEFUL_CHOICES = (("YES", "Yes"), ("NO", "No"))


class Feedback(TimeStampedModel):
    found_useful = models.CharField(
        blank=True, max_length=100, choices=FOUND_USEFUL_CHOICES
    )
    sources = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    source_url = models.CharField(blank=True, max_length=800)
    token = models.CharField(blank=True, max_length=100)
