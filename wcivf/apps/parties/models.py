from django.urls import reverse
from django.db import models
from django.utils.text import slugify

from elections.models import Election


class PartyManager(models.Manager):
    def update_or_create_from_ynr(self, party):
        defaults = {"party_name": party["name"]}

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
    emblem_url = models.URLField(blank=True, null=True)
    wikipedia_url = models.URLField(blank=True)
    description = models.TextField(blank=True)

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


class LocalParty(models.Model):
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
