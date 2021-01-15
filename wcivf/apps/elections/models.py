import datetime
import pytz

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.urls import reverse
from django.db import models
from django.utils.html import mark_safe
from django.utils.text import slugify

from .helpers import expected_sopn_publish_date
from .managers import ElectionManager

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
    voting_system = models.ForeignKey(
        "VotingSystem", null=True, blank=True, on_delete=models.CASCADE
    )
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

    @property
    def in_past(self):
        """
        Returns a boolean for whether the election date is in the past
        """
        return self.election_date < datetime.date.today()

    @property
    def is_city_of_london(self):
        """
        Returns boolean for if the election is within City of London district.
        The city often has different rules to other UK elections so it's useful
        to know when we need to special case. For further details:
        https://www.cityoflondon.gov.uk/about-us/voting-elections/elections/ward-elections
        https://democracyclub.org.uk/blog/2017/03/22/eight-weird-things-about-tomorrows-city-london-elections/
        """
        return "local.city-of-london" in self.slug

    @property
    def polls_close(self):
        """
        Return a time object for the time the polls close.
        Polls close earlier in City of London, for more info:
        https://www.cityoflondon.gov.uk/about-us/voting-elections/elections/ward-elections
        https://democracyclub.org.uk/blog/2017/03/22/eight-weird-things-about-tomorrows-city-london-elections/
        """
        if self.is_city_of_london:
            return datetime.time(20, 0)

        return datetime.time(22, 0)

    @property
    def polls_open(self):
        """
        Return a time object for the time polls open.
        Polls open later in City of London, for more info:
        https://www.cityoflondon.gov.uk/about-us/voting-elections/elections/ward-elections
        https://democracyclub.org.uk/blog/2017/03/22/eight-weird-things-about-tomorrows-city-london-elections/
        """
        if self.is_city_of_london:
            return datetime.time(8, 0)

        return datetime.time(7, 0)

    @property
    def is_election_day(self):
        """
        Return boolean for whether it is election day
        """
        return self.election_date == datetime.date.today()

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
        return utc_to_local(election_datetime.replace(hour=7))

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
    organization_type = models.CharField(blank=True, max_length=100)
    area_name = models.CharField(blank=True, max_length=100)
    area_id = models.CharField(blank=True, max_length=100)
    territory = models.CharField(blank=True, max_length=3)
    elections = models.ManyToManyField(
        Election, through="elections.PostElection"
    )

    def nice_organization(self):
        return (
            self.organization.replace(" County Council", "")
            .replace(" Borough Council", "")
            .replace(" District Council", "")
            .replace("London Borough of ", "")
            .replace(" Council", "")
        )

    def nice_territory(self):
        if self.territory == "WLS":
            return "Wales"

        if self.territory == "ENG":
            return "England"

        if self.territory == "SCT":
            return "Scotland"

        if self.territory == "NIR":
            return "Northern Ireland"

        return self.territory


class PostElection(models.Model):
    ballot_paper_id = models.CharField(blank=True, max_length=800, unique=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    contested = models.BooleanField(default=True)
    winner_count = models.IntegerField(blank=True, null=True)
    locked = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)
    replaced_by = models.ForeignKey(
        "PostElection",
        null=True,
        blank=True,
        related_name="replaces",
        on_delete=models.CASCADE,
    )
    metadata = JSONField(null=True)
    voting_system = models.ForeignKey(
        "VotingSystem", null=True, blank=True, on_delete=models.CASCADE
    )
    wikipedia_url = models.CharField(blank=True, null=True, max_length=800)
    wikipedia_bio = models.TextField(null=True)

    def get_name_suffix(self):
        election_type = self.ballot_paper_id.split(".")[0]
        if election_type == "local":
            return "ward"
        if election_type == "parl":
            return "constituency"
        if election_type == "europarl":
            return "region"
        return "area"

    def expected_sopn_date(self):
        return expected_sopn_publish_date(
            self.ballot_paper_id, self.post.territory
        )

    def friendly_name(self):
        # TODO Take more info from YNR/EE about the election
        # rather than hard coding not_wards and not_by_elections
        name = self.post.label

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
    def ynr_sopn_link(self):
        return "{}/elections/{}/sopn/?{}".format(
            settings.YNR_BASE,
            self.ballot_paper_id,
            settings.YNR_UTM_QUERY_STRING,
        )

    @property
    def short_cancelled_message_html(self):
        if not self.cancelled:
            return ""
        message = None
        if self.metadata and self.metadata.get("cancelled_election"):
            title = self.metadata["cancelled_election"].get("title")
            url = self.metadata["cancelled_election"].get("url")
            message = title
            if url:
                message = """<strong> ❌ <a href="{}">{}</a></strong>""".format(
                    url, title
                )
        if not message:
            if self.election.in_past:
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

    @property
    def display_as_party_list(self):
        if (
            self.get_voting_system
            and self.get_voting_system.slug in settings.PARTY_LIST_VOTING_TYPES
        ):
            return True
        return False


class VotingSystem(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(blank=True, max_length=100)
    wikipedia_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    @property
    def uses_party_lists(self):
        return self.slug in ["PR-CL", "AMS"]
