from django.db import models

from people.models import Person


class CV(models.Model):
    """
    A candidate's CV.
    """

    person = models.OneToOneField(Person, on_delete=models.CASCADE)
    url = models.URLField(blank=True, null=True)
    thumb_url = models.URLField(blank=True, null=True)
    last_modified = models.DateTimeField(blank=True, null=True)
