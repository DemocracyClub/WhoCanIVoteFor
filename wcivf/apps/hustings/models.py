"""
Models for Hustings
"""
import datetime

from django.db import models

from elections.models import PostElection


class Husting(models.Model):
    """
    A Husting.
    """

    post_election = models.ForeignKey(PostElection, on_delete=models.CASCADE)
    title = models.CharField(max_length=250)
    url = models.URLField()
    starts = models.DateTimeField()
    ends = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=250, blank=True, null=True)
    postcode = models.CharField(max_length=10, blank=True, null=True)
    postevent_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ["-starts"]

    def in_past(self):
        return self.starts.date() < datetime.date.today()
