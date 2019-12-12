from django.db import models

from people.models import Person


class LeafletQuerySet(models.QuerySet):
    def latest_four(self):
        return self.order_by("date_uploaded_to_electionleaflets")[:4]


class Leaflet(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    leaflet_id = models.IntegerField()
    thumb_url = models.URLField(null=True, blank=True)
    date_uploaded_to_electionleaflets = models.DateTimeField(
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = LeafletQuerySet.as_manager()
