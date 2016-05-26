import datetime
import pytz

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.text import slugify


from .managers import ElectionManager, PostManager

LOCAL_TZ = pytz.timezone("Europe/London")


class InvalidPostcodeError(Exception):
    pass


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(LOCAL_TZ)


class Election(models.Model):
    slug = models.CharField(max_length=128, unique=True)
    election_date = models.DateField()
    name = models.CharField(max_length=128)
    current = models.BooleanField()
    description = models.TextField(blank=True)
    ballot_colour = models.CharField(blank=True, max_length=100)
    election_type = models.CharField(blank=True, max_length=100)
    voting_system = models.ForeignKey('VotingSystem', null=True, blank=True)
    uses_lists = models.BooleanField(default=False)
    voter_age = models.CharField(blank=True, max_length=100)
    voter_citizenship = models.TextField(blank=True)
    for_post_role = models.TextField(blank=True)
    election_weight = models.IntegerField(default=10)

    objects = ElectionManager()

    class Meta:
        ordering = ['election_date']

    def __str__(self):
        return self.name

    def in_past(self):
        return self.election_date < datetime.date.today()

    def friendly_day(self):
        delta = self.election_date - datetime.date.today()

        if delta.days == 0:
            return_str = "today"
        elif delta.days < 0:
            if delta.days == -1:
                return_str = "yesterday"
            elif delta.days > -5:
                return_str = "{} days ago".format(delta.days)
            else:
                return_str = "on {}".format(self.election_date.strftime("%A %-d %B %Y"))
        else:
            if delta.days == 1:
                return_str = "tomorrow"
            elif delta.days < 7:
                return_str = "in {} days".format(delta.days)
            else:
                return_str = "on {}".format(self.election_date.strftime("%A %-d %B %Y"))

        if not return_str.startswith("on "):
            return_str += " ({})".format(self.election_date.strftime("%A %-d %B %Y"))

        return return_str


    @property
    def nice_election_name(self):
        if self.election_type == "local":
            return "Local"
        if self.election_type == "sp":
            return "Scottish parliament"
        if self.election_type == "naw":
            return "Welsh assembly"
        if self.election_type == "gla":
            return "Greater London assembly"
        if self.election_type == "pcc":
            return "Police and crime commissioner"
        if self.election_type == "mayor":
            return "City mayor"
        if self.election_type == "nia":
            return "Northern Ireland assembly"
        return self.name

    def _election_datetime_tz(self):
        election_date = self.election_date
        election_datetime = datetime.datetime.fromordinal(
            election_date.toordinal())
        election_datetime.replace(tzinfo=LOCAL_TZ)
        return election_datetime

    @property
    def start_time(self):
        election_datetime = self._election_datetime_tz()
        return utc_to_local(election_datetime.replace(hour=6))

    @property
    def end_time(self):
        election_datetime = self._election_datetime_tz()
        return utc_to_local(election_datetime.replace(hour=22))

    def get_absolute_url(self):
        return reverse('election_view', args=[
            str(self.slug),
            slugify(self.name)
        ])


class Post(models.Model):
    """
    A post has an election and candidates
    """
    ynr_id = models.CharField(blank=True, max_length=100, primary_key=True)
    label = models.CharField(blank=True, max_length=255)
    role = models.CharField(blank=True, max_length=255)
    group = models.CharField(blank=True, max_length=100)
    organization = models.CharField(blank=True, max_length=100)
    area_name = models.CharField(blank=True, max_length=100)
    area_id = models.CharField(blank=True, max_length=100)
    election = models.ForeignKey(Election)

    objects = PostManager()

    def get_absolute_url(self):
        return reverse('post_view', args=[
                str(self.election.slug),
                str(self.ynr_id),
                slugify(self.label)
            ])


    def friendly_name(self):
        if self.ynr_id == "ref.2016-06-23":
            return self.label
        return "{} for {}".format(self.election.for_post_role, self.area_name)


class VotingSystem(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(blank=True, max_length=100)
    wikipedia_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
