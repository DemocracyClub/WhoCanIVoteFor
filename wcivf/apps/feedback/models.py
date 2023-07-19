import uuid

from django.db import models

from django_extensions.db.models import TimeStampedModel
from django.utils.translation import gettext_lazy as _

FOUND_USEFUL_CHOICES = (("YES", _("Yes")), ("NO", _("No")))
VOTE_CHOICES = (("YES", _("Yes")), ("NO", _("No")))


def generate_feedback_token():
    return uuid.uuid4().hex


class Feedback(TimeStampedModel):
    found_useful = models.CharField(
        blank=True, max_length=100, choices=FOUND_USEFUL_CHOICES
    )
    vote = models.CharField(blank=True, max_length=100, choices=VOTE_CHOICES)
    sources = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    source_url = models.CharField(blank=True, max_length=800)
    token = models.CharField(
        blank=True, max_length=100, default=generate_feedback_token
    )
    flagged_as_spam = models.BooleanField(default=False)
