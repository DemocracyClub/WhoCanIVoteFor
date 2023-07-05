from django.urls import reverse
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import get_language
from model_utils.models import TimeStampedModel

from elections.models import Election


class PartyManager(models.Manager):
    def update_or_create_from_ynr(self, party):
        defaults = {
            "party_name": party["name"],
            "ec_id": party["ec_id"],
            "register": party["register"],
            "status": party["status"],
            "date_registered": party["date_registered"],
            "date_deregistered": party["date_deregistered"],
            "alternative_name": party["alternative_name"],
        }

        if party["default_emblem"]:
            defaults["emblem_url"] = party["default_emblem"]["image"]

        party_obj, _ = self.update_or_create(
            party_id=party["legacy_slug"], defaults=defaults
        )

        return (party_obj, _)


class Party(models.Model):
    """
    Represents a UK political party.
    """

    party_id = models.CharField(blank=True, max_length=100, primary_key=True)
    party_name = models.CharField(max_length=765)
    alternative_name = models.CharField(max_length=765, null=True)
    emblem_url = models.URLField(blank=True, null=True)
    wikipedia_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    ec_id = models.CharField(
        db_index=True,
        max_length=25,
        unique=True,
        null=True,
        verbose_name="Electoral Commission Idenfitier",
        help_text="""
            An ID issued by The Electoral Commission in their party register,
            with the exception of Democracy Club psuedo IDs for special parties
        """,
    )
    register = models.CharField(
        max_length=2,
        db_index=True,
        null=True,
        verbose_name="Party register",
        help_text="""
                Normally either `GB` or `NI` depending on the
                country the party is registered in. Pseudo-parties don't have a
                register, so this field is nullable.
            """,
    )
    status = models.CharField(
        db_index=True,
        max_length=255,
        verbose_name="Party registration status",
        choices=[
            ("Registered", "Registered"),
            ("Deregistered", "Deregistered"),
        ],
        default="Registered",
    )
    date_registered = models.DateField(null=True)
    date_deregistered = models.DateField(null=True)

    class Meta:
        verbose_name_plural = "Parties"
        ordering = ("party_name",)

    objects = PartyManager()

    def __str__(self):
        return "%s (%s)" % (self.party_name, self.pk)

    def get_absolute_url(self):
        return reverse(
            "party_view", args=[str(self.pk), slugify(self.party_name)]
        )

    @property
    def is_independent(self):
        """
        Returns a boolean for whether the party has the internal ID that we use
        to identify a party as independent or no party. Further info:
        https://candidates.democracyclub.org.uk/api/docs/next/definitions/#Party
        """
        return self.party_id == "ynmp-party:2"

    @property
    def is_joint_party(self):
        return self.party_id.startswith("joint-party:")

    @property
    def is_speaker(self):
        """
        Returns a boolean for whether the party has the internal ID that we use
        to identify Speaker Seeking Re-election.
        """
        return self.party_id == "ynmp-party:12522"

    @property
    def get_joint_party_sub_parties(self):
        """
        A joint party in our system has an id of "joint-party:{party_id}-{party_id}".
        This function looks up a joint party's individual party records and returns
        a queryset containing the sub-parties
        """
        if self.is_joint_party:
            sub_party_numeric_ids = self.party_id.rsplit(":")[1].split("-")

            sub_parties = Party.objects.filter(
                party_id__in=[
                    f"party:{party_id}" for party_id in sub_party_numeric_ids
                ]
            )
            return sub_parties

        return None

    @property
    def is_deregistered(self):
        if not self.date_deregistered:
            return False
        return self.date_deregistered < timezone.now().date()

    @property
    def format_name(self):
        name = self.party_name
        if self.is_deregistered:
            name = f"{name} (Deregistered)"
        return name

    @property
    def get_party_register_url(self):
        if self.ec_id == self.party_id or not self.ec_id:
            # If an EC ID matches a party ID, that EC ID is in legacy slug
            # format and cannot be used to generate a party register URL.
            # This applies to indies, joint parties and the speaker.
            return None

        url_language = "English"
        if get_language() == "cy":
            url_language = "Cymraeg"
        return f"https://search.electoralcommission.org.uk/{url_language}/Registrations/{self.ec_id}"

    @property
    def format_register(self):
        """
        Returns a nice name for the register code
        """
        if self.register == "GB":
            return "Great Britain"

        if self.register == "NI":
            return "Northern Ireland"

        return None


class PartyDescriptionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(active=True)

    def inactive(self):
        return self.filter(active=False)


class PartyDescription(TimeStampedModel):
    """
    A party can register one or more descriptions with The Electoral Commission.

    Each description can be used by a candidate on a ballot paper, along side
    their name and chosen emblem.
    """

    party = models.ForeignKey(
        Party, on_delete=models.CASCADE, related_name="party_descriptions"
    )

    description = models.CharField(max_length=800)
    date_description_approved = models.DateField(null=True)
    active = models.BooleanField(default=False)

    objects = PartyDescriptionQuerySet.as_manager()

    class Meta:
        unique_together = (
            "party",
            "description",
        )

        ordering = ["-active", "date_description_approved"]


class PartyEmblemQuerySet(models.QuerySet):
    def active(self):
        return self.filter(active=True)

    def inactive(self):
        return self.filter(active=False)


class PartyEmblem(TimeStampedModel):
    party = models.ForeignKey(
        Party, on_delete=models.CASCADE, related_name="emblems"
    )
    ec_emblem_id = models.PositiveIntegerField(primary_key=True)
    emblem_url = models.TextField(null=True)
    description = models.CharField(max_length=255)
    date_approved = models.DateField(null=True)
    default = models.BooleanField(default=False)
    active = models.BooleanField(default=False)

    objects = PartyEmblemQuerySet.as_manager()

    class Meta:
        ordering = ("-default", "-active", "ec_emblem_id")


class LocalParty(TimeStampedModel):
    parent = models.ForeignKey(
        Party, related_name="local_parties", on_delete=models.CASCADE
    )
    post_election = models.ForeignKey(
        "elections.PostElection", on_delete=models.CASCADE
    )
    name = models.CharField(blank=True, max_length=100)
    twitter = models.CharField(blank=True, max_length=100)
    facebook_page = models.URLField(blank=True, max_length=800)
    homepage = models.URLField(blank=True, max_length=800)
    email = models.EmailField(blank=True)
    is_local = models.BooleanField(
        default=True,
        help_text="Used to identify if obj is related to a local election",
    )
    youtube_profile_url = models.URLField(blank=True, max_length=800)
    contact_page_url = models.URLField(blank=True, max_length=800)
    file_url = models.URLField(
        blank=True,
        max_length=800,
        help_text="The url to the google sheet the object was imported from. Not to be displayed.",
    )

    def __str__(self):
        return self.name

    @property
    def label(self):
        """
        Return a string with 'the' added if the name ends with 'Party'
        """
        if self.name.lower().endswith("party"):
            return f"the {self.name}"
        return self.name


class Manifesto(models.Model):
    COUNTRY_CHOICES = (
        ("UK", "UK"),
        ("England", "England"),
        ("Scotland", "Scotland"),
        ("Wales", "Wales"),
        ("Northern Ireland", "Northern Ireland"),
        ("Local", "Local"),
    )
    LANGUAGE_CHOICES = (("English", "English"), ("Welsh", "Welsh"))
    party = models.ForeignKey(Party, on_delete=models.CASCADE)
    election = models.ForeignKey(Election, on_delete=models.CASCADE)
    country = models.CharField(
        max_length=200, choices=COUNTRY_CHOICES, default="UK"
    )
    language = models.CharField(
        max_length=200, choices=LANGUAGE_CHOICES, default="English"
    )
    pdf_url = models.URLField(blank=True, max_length=800)
    web_url = models.URLField(blank=True, max_length=800)
    easy_read_url = models.URLField(blank=True, max_length=800)
    file_url = models.URLField(
        blank=True,
        max_length=800,
        help_text="The url to the google sheet the object was imported from. Not to be displayed.",
    )

    def __str__(self):
        canonical_url = self.canonical_url()
        str = "<a href='%s'>" % canonical_url
        str += "%s manifesto" % (self.country)
        if self.language != "English":
            str += " in %s" % self.language
        str += "</a>"
        if canonical_url == self.pdf_url:
            str += " (PDF)"
        return str

    def canonical_url(self):
        canonical_url = self.pdf_url
        if self.web_url:
            canonical_url = self.web_url
        return canonical_url

    def save(self, *args, **kwargs):
        if self.pdf_url or self.web_url:
            super(Manifesto, self).save(*args, **kwargs)
        else:
            print("Manifesto must have either a web or PDF URL")

    class Meta:
        ordering = ["-country", "language"]
        unique_together = ("party", "election", "country", "language")
