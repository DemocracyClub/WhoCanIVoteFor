from django.db import models
from django_extensions.db.models import TimeStampedModel


class BallotNewsArticle(TimeStampedModel):
    ballot = models.ForeignKey(
        "elections.PostElection", on_delete=models.CASCADE
    )
    url = models.URLField(max_length=800)
    title = models.CharField(max_length=800)
    summary = models.TextField()
    publisher = models.CharField(max_length=500, blank=True)
