import datetime
import re

from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import pytz
from django.conf import settings
from django.db.models import JSONField, DateTimeField
from django.db import models
from django.template.defaultfilters import pluralize
from django.contrib.humanize.templatetags.humanize import apnumber
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.html import mark_safe
from django.utils.text import slugify

from django_extensions.db.models import TimeStampedModel

from .helpers import get_election_timetable
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
        ordering = ["election_date", "election_weight"]

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

    @property
    def name_without_brackets(self):
        """
        Removes any characters from the election name after an opening bracket
        TODO name this see if we can do this more reliably based on data from
        EE
        """
        regex = r"\(.*?\)"
        brackets_removed = re.sub(regex, "", self.nice_election_name)
        # remove any extra whitespace
        return brackets_removed.replace("  ", " ").strip()

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
            "mayor.bristol.2021-05-06": "booklets/2021-05-06/mayoral/mayor.bristol.2021-05-06.pdf",
            "mayor.cambridgeshire-and-peterborough.2021-05-06": "booklets/2021-05-06/mayoral/mayor.cambridgeshire-and-peterborough.2021-05-06.pdf",
            "mayor.doncaster.2021-05-06": "booklets/2021-05-06/mayoral/mayor.doncaster.2021-05-06.pdf",
            "mayor.greater-manchester-ca.2021-05-06": "booklets/2021-05-06/mayoral/mayor.greater-manchester-ca.2021-05-06.pdf",
            "mayor.liverpool-city-ca.2021-05-06": "booklets/2021-05-06/mayoral/mayor.liverpool-city-ca.2021-05-06.pdf",
            "mayor.london.2021-05-06": "booklets/2021-05-06/mayoral/mayor.london.2021-05-06.pdf",
            "mayor.north-tyneside.2021-05-06": "booklets/2021-05-06/mayoral/mayor.north-tyneside.2021-05-06.pdf",
            "mayor.salford.2021-05-06": "booklets/2021-05-06/mayoral/mayor.salford.2021-05-06.pdf",
            "mayor.tees-valley.2021-05-06": "booklets/2021-05-06/mayoral/mayor.tees-valley.2021-05-06.pdf",
            "mayor.west-midlands.2021-05-06": "booklets/2021-05-06/mayoral/mayor.west-midlands.2021-05-06.pdf",
            "mayor.west-of-england.2021-05-06": "booklets/2021-05-06/mayoral/mayor.west-of-england.2021-05-06.pdf",
            "mayor.west-yorkshire.2021-05-06": "booklets/2021-05-06/mayoral/mayor.west-yorkshire.2021-05-06.pdf",
            "mayor.croydon.2022-05-05": "booklets/2022-05-05/mayoral/mayor.croydon.2022-05-05.pdf",
            "mayor.hackney.2022-05-05": "booklets/2022-05-05/mayoral/mayor.hackney.2022-05-05.pdf",
            "mayor.lewisham.2022-05-05": "booklets/2022-05-05/mayoral/mayor.lewisham.2022-05-05.pdf",
            "mayor.newham.2022-05-05": "booklets/2022-05-05/mayoral/mayor.newham.2022-05-05.pdf",
            "mayor.sheffield-city-ca.2022-05-05": "booklets/2022-05-05/mayoral/mayor.sheffield-city-ca.2022-05-05.pdf",
            "mayor.tower-hamlets.2022-05-05": "booklets/2022-05-05/mayoral/mayor.tower-hamlets.2022-05-05.pdf",
        }

        return election_to_booklet.get(self.slug)

    @property
    def ynr_link(self):
        return "{}/election/{}/constituencies?{}".format(
            settings.YNR_BASE, self.slug, settings.YNR_UTM_QUERY_STRING
        )

    @cached_property
    def pluralized_division_name(self):
        """
        Returns a string for the pluralised divison name for the posts in the
        election
        """
        pluralise = {
            "parish": "parishes",
            "constituency": "constituencies",
        }
        suffix = self.post_set.first().division_suffix

        if not suffix:
            return "posts"

        return pluralise.get(suffix, f"{suffix}s")


class Post(models.Model):
    """
    A post has an election and candidates
    """

    DIVISION_TYPE_CHOICES = [
        ("CED", "County Electoral Division"),
        ("COP", "Isles of Scilly Parish"),
        ("DIW", "District Ward"),
        ("EUR", "European Parliament Region"),
        ("LAC", "London Assembly Constituency"),
        ("LBW", "London Borough Ward"),
        ("LGE", "NI Electoral Area"),
        ("MTW", "Metropolitan District Ward"),
        ("NIE", "NI Assembly Constituency"),
        ("SPC", "Scottish Parliament Constituency"),
        ("SPE", "Scottish Parliament Region"),
        ("UTE", "Unitary Authority Electoral Division"),
        ("UTW", "Unitary Authority Ward"),
        ("WAC", "Welsh Assembly Constituency"),
        ("WAE", "Welsh Assembly Region"),
        ("WMC", "Westminster Parliamentary Constituency"),
    ]

    ynr_id = models.CharField(max_length=100, primary_key=True)
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
    division_type = models.CharField(
        blank=True, max_length=3, choices=DIVISION_TYPE_CHOICES
    )

    def __str__(self) -> str:
        return f"{self.label} ({self.ynr_id})"

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

    @property
    def division_description(self):
        """
        Return a string to describe the division.
        """
        mapping = {
            choice[0]: choice[1] for choice in self.DIVISION_TYPE_CHOICES
        }
        return mapping.get(self.division_type, "")

    @property
    def division_suffix(self):
        """
        Returns last word of the division_description
        """
        description = self.division_description
        if not description:
            return ""
        return description.split(" ")[-1].lower()

    @property
    def full_label(self):
        """
        Returns label with division suffix
        """
        return f"{self.label} {self.division_suffix}".strip()


class PostElectionQuerySet(models.QuerySet):
    def last_updated_in_ynr(self):
        """
        Returns the ballot with the most recent change made in YNR we know about
        """
        return self.filter(ynr_modified__isnull=False).latest("ynr_modified")

    def modified_gt_with_related(self, date):
        """
        Finds related models that have been updated
        since a given date and returns a queryset of PostElections
        """
        return (
            self.annotate(
                last_updated=Greatest(
                    "modified",
                    "husting__modified",
                    "localparty__modified",
                    output_field=DateTimeField(),
                ),
            )
            .filter(last_updated__gt=date)
            .order_by("last_updated")
        )


class PostElection(TimeStampedModel):
    ballot_paper_id = models.CharField(blank=True, max_length=800, unique=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    contested = models.BooleanField(default=True)
    winner_count = models.IntegerField(blank=True, default=1)
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
    ynr_modified = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of when this ballot was updated in the YNR",
    )
    requires_voter_id = models.CharField(blank=True, null=True, max_length=50)

    objects = PostElectionQuerySet.as_manager()

    class Meta:
        get_latest_by = "ynr_modified"

    @property
    def expected_sopn_date(self):
        try:
            return get_election_timetable(
                self.ballot_paper_id, self.post.territory
            ).sopn_publish_date
        except AttributeError:
            return None

    @property
    def registration_deadline(self):
        return get_election_timetable(
            self.ballot_paper_id, self.post.territory
        ).registration_deadline

    @property
    def past_registration_deadline(self):
        return self.registration_deadline < datetime.date.today()

    @property
    def postal_vote_application_deadline(self):
        return get_election_timetable(
            self.ballot_paper_id, self.post.territory
        ).postal_vote_application_deadline

    @property
    def is_mayoral(self):
        """
        Return a boolean for if this is a mayoral election, determined by
        checking ballot paper id
        """
        return self.ballot_paper_id.startswith("mayor")

    @property
    def is_parliamentary(self):
        """
        Return a boolean for if this is a parliamentary election, determined by
        checking ballot paper id
        """
        return self.ballot_paper_id.startswith("parl")

    @property
    def is_london_assembly_additional(self):
        """
        Return a boolean for if this is a London Assembley additional ballot
        """
        return self.ballot_paper_id.startswith("gla.a")

    @property
    def is_pcc(self):
        """
        Return a boolean for if this is a PCC ballot
        """
        return self.ballot_paper_id.startswith("pcc")

    @property
    def is_constituency(self):
        return self.ballot_paper_id.startswith(("gla.c", "senedd.c", "sp.c"))

    @property
    def is_regional(self):
        return self.ballot_paper_id.startswith(("gla.r", "senedd.r", "sp.r"))

    @property
    def is_referendum(self):
        """
        Return a boolean for if this is a Referendum ballot
        """
        return self.ballot_paper_id.startswith("ref.")

    @property
    def friendly_name(self):
        """
        Helper property used in templates to build a 'friendly' name using
        details from associated Post object, with exceptions for mayoral and
        Police and Crime Commissioner elections
        """
        if self.is_mayoral:
            return f"{self.post.full_label} mayoral election"

        if self.is_pcc:
            label = self.post.full_label.replace(" Police", "")
            return f"{label} Police force area"

        return self.post.full_label

    def get_absolute_url(self):
        if self.ballot_paper_id.startswith("tmp_"):
            return reverse("home_view")
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

    @cached_property
    def next_ballot(self):
        """
        Return the next ballot for the related post. Return None if this is
        the current election to avoid making an unnecessary db query.
        """
        if self.election.current:
            return None

        try:
            return self.post.postelection_set.filter(
                election__election_date__gt=self.election.election_date,
                election__election_date__gte=datetime.date.today(),
                election__election_type=self.election.election_type,
            ).latest("election__election_date")
        except PostElection.DoesNotExist:
            return None

    @property
    def party_ballot_count(self):
        if self.personpost_set.exists():
            people = self.personpost_set
            if self.election.uses_lists:
                ind_candidates = people.filter(party_id="ynmp-party:2").count()
                num_other_parties = (
                    people.exclude(party_id="ynmp-party:2")
                    .values("party_id")
                    .distinct()
                    .count()
                )
                ind_and_parties = ind_candidates + num_other_parties
                ind_and_parties_apnumber = apnumber(ind_and_parties)
                ind_and_parties_pluralized = pluralize(ind_and_parties)
                value = f"{ind_and_parties_apnumber} parties"
                if ind_candidates:
                    value = f"{value} or independent candidate{ind_and_parties_pluralized}"
                return value

            else:
                num_candidates = people.count()
                candidates_apnumber = apnumber(num_candidates)
                candidates_pluralized = pluralize(num_candidates)
                return f"{candidates_apnumber} candidate{candidates_pluralized}"

    @property
    def should_display_sopn_info(self):
        """
        Return boolean for whether to display text about SOPN
        """
        if self.election.in_past:
            return False

        if self.locked:
            return True

        return bool(self.expected_sopn_date)

    @property
    def past_expected_sopn_day(self):
        """
        Return boolean for if the date we expected the sopn date
        """
        return self.expected_sopn_date <= timezone.now().date()

    @property
    def should_show_candidates(self):
        if not self.cancelled:
            return True
        if not self.metadata:
            return True
        if reason := self.metadata.get("cancelled_election", {}).get(
            "cancellation_reason", ""
        ):
            if reason == "CANDIDATE_DEATH":
                return False
            if reason == "EQUAL_CANDIDATES":
                return True
            if reason == "UNDER_CONTESTED":
                return True
        return True


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

    @property
    def get_absolute_url(self):
        if self.slug == "FPTP":
            return reverse("fptp_voting_system_view")
        elif self.slug == "AMS":
            return reverse("ams_voting_system_view")
        elif self.slug == "sv":
            return reverse("sv_voting_system_view")
        elif self.slug == "STV":
            return reverse("stv_voting_system_view")
        else:
            None

    @property
    def get_name(self):
        if self.slug == "FPTP":
            return _("First-past-the-post")
        elif self.slug == "AMS":
            return _("Additional Member System")
        elif self.slug == "sv":
            return _("Supplementary Vote")
        elif self.slug == "STV":
            return _("Single Transferable Vote")
        else:
            None
