import datetime
import pytz

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.html import mark_safe
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
    voting_system = models.ForeignKey("VotingSystem", null=True, blank=True)
    uses_lists = models.BooleanField(default=False)
    voter_age = models.CharField(blank=True, max_length=100)
    voter_citizenship = models.TextField(blank=True)
    for_post_role = models.TextField(blank=True)
    election_weight = models.IntegerField(default=10)
    metadata = JSONField(null=True)
    any_non_by_elections = models.BooleanField(default=False)

    objects = ElectionManager()

    class Meta:
        ordering = ["election_date"]

    def __str__(self):
        return self.name

    def in_past(self):
        return self.election_date < datetime.date.today()

    def friendly_day(self):
        delta = self.election_date - datetime.date.today()

        if delta.days == 0:
            return "today"
        elif delta.days < 0:
            if delta.days == -1:
                return "yesterday"
            elif delta.days > -5:
                return "{} days ago".format(delta.days)
            else:
                return "on {}".format(
                    self.election_date.strftime("%A %-d %B %Y")
                )
        else:
            if delta.days == 1:
                return "tomorrow"
            elif delta.days < 7:
                return "in {} days".format(delta.days)
            else:
                return "on {}".format(
                    self.election_date.strftime("%A %-d %B %Y")
                )

    @property
    def nice_election_name(self):

        name = self.name
        if not self.any_non_by_elections:
            name = name.replace("elections", "")
            name = name.replace("election", "")
            name = name.replace("UK Parliament", "UK Parliamentary")
            name = "{} {}".format(name, "by-election")
        if self.election_type == "mayor":
            name = name.replace("election", "")

        return name

    def _election_datetime_tz(self):
        election_date = self.election_date
        election_datetime = datetime.datetime.fromordinal(
            election_date.toordinal()
        )
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
        return reverse(
            "election_view", args=[str(self.slug), slugify(self.name)]
        )

    def election_booklet(self):
        election_to_booklet = {
            "mayor.greater-manchester-ca.2017-05-04": "booklets/2017-05-04/mayoral/mayor.greater-manchester-ca.2017-05-04.pdf",
            "mayor.liverpool-city-ca.2017-05-04": "booklets/2017-05-04/mayoral/mayor.liverpool-city-ca.2017-05-04.pdf",
            "mayor.cambridgeshire-and-peterborough.2017-05-04": "booklets/2017-05-04/mayoral/mayor.cambridgeshire-and-peterborough.2017-05-04.pdf",  # noqa
            "mayor.west-of-england.2017-05-04": "booklets/2017-05-04/mayoral/mayor.west-of-england.2017-05-04.pdf",
            "mayor.west-midlands.2017-05-04": "booklets/2017-05-04/mayoral/mayor.west-midlands.2017-05-04.pdf",
            "mayor.tees-valley.2017-05-04": "booklets/2017-05-04/mayoral/mayor.tees-valley.2017-05-04.pdf",
            "mayor.north-tyneside.2017-05-04": "booklets/2017-05-04/mayoral/mayor.north-tyneside.2017-05-04.pdf",
            "mayor.doncaster.2017-05-04": "booklets/2017-05-04/mayoral/mayor.doncaster.2017-05-04.pdf",
            "mayor.hackney.2018-05-03": "booklets/2018-05-03/mayoral/mayor.hackney.2018-05-03.pdf",
            "mayor.sheffield-city-ca.2018-05-03": "booklets/2018-05-03/mayoral/mayor.sheffield-city-ca.2018-05-03.pdf",
            "mayor.lewisham.2018-05-03": "booklets/2018-05-03/mayoral/mayor.lewisham.2018-05-03.pdf",
            "mayor.tower-hamlets.2018-05-03": "booklets/2018-05-03/mayoral/mayor.tower-hamlets.2018-05-03.pdf",
            "mayor.newham.2018-05-03": "booklets/2018-05-03/mayoral/mayor.newham.2018-05-03.pdf",
        }

        return election_to_booklet.get(self.slug)

    @property
    def ynr_link(self):
        return "{}/election/{}/constituencies?{}".format(
            settings.YNR_BASE, self.slug, settings.YNR_UTM_QUERY_STRING
        )


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
    elections = models.ManyToManyField(
        Election, through="elections.PostElection"
    )

    objects = PostManager()


class PostElection(models.Model):
    ballot_paper_id = models.CharField(blank=True, max_length=800, unique=True)
    post = models.ForeignKey(Post)
    election = models.ForeignKey(Election)
    contested = models.BooleanField(default=True)
    winner_count = models.IntegerField(blank=True, null=True)
    locked = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    replaced_by = models.ForeignKey(
        "PostElection", null=True, blank=True, related_name="replaces"
    )
    metadata = JSONField(null=True)
    voting_system = models.ForeignKey("VotingSystem", null=True, blank=True)

    def get_name_suffix(self):
        election_type = self.ballot_paper_id.split(".")[0]
        if election_type == "local":
            return "ward"
        if election_type == "parl":
            return "constituency"
        if election_type == "europarl":
            return "region"
        return "area"

    def friendly_name(self):
        # TODO Take more info from YNR/EE about the election
        # rather than hard coding not_wards and not_by_elections
        name = self.post.area_name

        suffix = self.get_name_suffix()
        if suffix:
            name = "{} {}".format(name, suffix)

        if ".by." in self.ballot_paper_id:
            name = "{} by-election".format(name)

        if self.ballot_paper_id.startswith("mayor"):
            return self.election.nice_election_name

        return name

    def get_absolute_url(self):
        return reverse(
            "election_view",
            args=[str(self.ballot_paper_id), slugify(self.post.label)],
        )

    @property
    def ynr_link(self):
        return "{}/elections/{}?{}".format(
            settings.YNR_BASE,
            self.ballot_paper_id,
            settings.YNR_UTM_QUERY_STRING,
        )

    @property
    def short_cancelled_message_html(self):
        if not self.cancelled:
            return ""
        if self.election.in_past():
            message = "(The poll for this election was cancelled)"
        else:
            message = "<strong>(The poll for this election has been cancelled)</strong>"
        return mark_safe(message)

    @property
    def get_voting_system(self):
        if self.voting_system:
            return self.voting_system
        else:
            return self.election.voting_system


class VotingSystem(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(blank=True, max_length=100)
    wikipedia_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
