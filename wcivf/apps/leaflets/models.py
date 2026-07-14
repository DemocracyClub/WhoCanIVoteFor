import datetime as dt

from django.db import models
from django.utils import timezone
from people.models import Person


class LeafletQuerySet(models.QuerySet):
    def latest_four(self):
        return self.filter(
            date_uploaded_to_electionleaflets__gte=timezone.now()
            - dt.timedelta(days=365)
        ).order_by("-date_uploaded_to_electionleaflets")[:4]


class Leaflet(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    leaflet_id = models.IntegerField()
    thumb_url = models.URLField(null=True, blank=True, max_length=800)
    date_uploaded_to_electionleaflets = models.DateTimeField(
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = LeafletQuerySet.as_manager()
