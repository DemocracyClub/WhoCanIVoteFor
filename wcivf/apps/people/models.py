from urllib.parse import urlparse

from django.contrib.humanize.templatetags.humanize import intcomma, ordinal
from django.db import models
from django.db.models import JSONField
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from elections.models import Election, Post
from parties.models import Party

from wcivf import settings

from .managers import VALUE_TYPES_TO_IMPORT, PersonManager, PersonPostManager


class PersonPost(models.Model):
    person = models.ForeignKey("Person", on_delete=models.CASCADE)
    post_election = models.ForeignKey(
        "elections.PostElection", null=False, on_delete=models.CASCADE
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    party = models.ForeignKey(Party, null=True, on_delete=models.CASCADE)
    party_name = models.CharField(
        max_length=255,
        help_text="The name of the party at the time of the candidacy",
    )
    party_description_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="The party description at the time of the candidacy",
    )
    election = models.ForeignKey(Election, null=False, on_delete=models.CASCADE)
    list_position = models.IntegerField(blank=True, null=True)
    elected = models.BooleanField(null=True)
    votes_cast = models.PositiveIntegerField(null=True)
    previous_party_affiliations = models.ManyToManyField(
        Party, related_name="affiliated_memberships", blank=True
    )
    rank = models.PositiveIntegerField(null=True)
    deselected = models.BooleanField(default=False)
    deselected_source = models.CharField(max_length=800, blank=True, null=True)

    objects = PersonPostManager()

    def __str__(self):
        return "{} ({}, {})".format(
            self.person.name, self.post.label, self.election.slug
        )

    def get_local_party(self):
        qs = self.party.local_parties.filter(post_election=self.post_election)
        if qs.exists:
            return qs.get()

        return None

    @property
    def get_results_text(self) -> str:
        """
        Text describing the outcome of the election, as relates to this person.

        For example, if they were elected and we have the vote count, return:

            "Elected (12345 votes)"
        """

        # Cancelled ballot:
        # If a ballot is marked "cancelled" it can mean two things for the
        # candidacy:
        #   1. The election was uncontested and this person ended up being
        #      'elected' unopposed
        #   2. There was another reason for the election being cancelled
        if self.post_election.cancelled:
            if self.elected:
                return _("Elected unopposed")
            return _("(election cancelled)")

        # If the election is in the past, we can't have results!
        # NOTE: this needs to be after the cancelled checks, as an election
        # is always cancelled before the election day(!)
        if "election" in self._state.fields_cache:
            election = self._state.fields_cache["election"]
        else:
            election = self.post_election.election

        if election and not election.in_past:
            return _("(Results due after %(date)s)") % {
                "date": election.election_date.strftime("%d %B %Y")
            }

        # If this candidacy was marked as elected, we need to show that!
        # But we might not always have votes case for them.
        # This is either because no one has gone and entered them, or
        # because it's not an election we don't support votes cast for
        # (e.g. non-FPTP)
        num_votes = intcomma(self.votes_cast)
        if self.elected:
            if self.votes_cast:
                return _("%(num_votes)s votes (elected)") % {
                    "num_votes": num_votes
                }
            return _("Elected (vote count not available)")

        # If we have votes cast, but we've not marked the candidacy as elected
        # then the person wasn't elected, but we should still show the votes
        # they got.
        if self.votes_cast:
            return _("%(num_votes)s votes (not elected)") % {
                "num_votes": num_votes
            }
        return _("Not elected (vote count not available)")

    @property
    def get_results_rank(self):
        """
        Returns a formatted string of the position of the candidate on the ballot.

        e.g "3rd / 5 candidates".

        Deals with joint placement too, e.g "Joint 2nd / 4 candidates".

        Returns None if the rank is unknown.

        """

        if not self.rank:
            return None

        election_info = PersonPost.objects.filter(
            post_election=self.post_election
        ).aggregate(
            candidate_count=models.Count("id"),
            tie_count=models.Count(
                "id",
                filter=models.Q(votes_cast=self.votes_cast, rank=self.rank),
            ),
        )

        has_tie = election_info["tie_count"] > 1
        candidate_count = election_info["candidate_count"]
        rank_ordinal = ordinal(self.rank)
        if has_tie:
            return ngettext(
                "Joint %(rank)s / %(count)d candidate",
                "Joint %(rank)s / %(count)d candidates",
                candidate_count,
            ) % {"rank": rank_ordinal, "count": candidate_count}
        # Complete sentence for regular rankings
        return ngettext(
            "%(rank)s / %(count)d candidate",
            "%(rank)s / %(count)d candidates",
            candidate_count,
        ) % {"rank": rank_ordinal, "count": candidate_count}

    class Meta:
        ordering = ("-election__election_date",)
        unique_together = ("person", "post", "election")


class Person(models.Model):
    ynr_id = models.IntegerField(primary_key=True)
    twfy_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(blank=True, max_length=255)
    sort_name = models.CharField(null=True, max_length=255)
    email = models.EmailField(null=True)
    gender = models.CharField(blank=True, max_length=255, null=True)
    birth_date = models.CharField(null=True, max_length=255)
    death_date = models.CharField(null=True, max_length=255)
    photo_url = models.URLField(blank=True, null=True)
    favourite_biscuit = models.CharField(null=True, max_length=800)
    last_updated = models.DateTimeField(default=timezone.now)

    # contact points
    twitter_username = models.CharField(blank=True, null=True, max_length=100)
    facebook_page_url = models.CharField(blank=True, null=True, max_length=800)
    facebook_personal_url = models.CharField(
        blank=True, null=True, max_length=800
    )
    linkedin_url = models.CharField(blank=True, null=True, max_length=800)
    homepage_url = models.CharField(blank=True, null=True, max_length=800)
    blog_url = models.CharField(blank=True, null=True, max_length=800)
    party_ppc_page_url = models.CharField(blank=True, null=True, max_length=800)
    instagram_url = models.CharField(blank=True, null=True, max_length=800)
    instagram_id = models.CharField(blank=True, null=True, max_length=800)
    youtube_profile = models.CharField(blank=True, null=True, max_length=800)
    mastodon_username = models.CharField(blank=True, null=True, max_length=800)
    tiktok_url = models.CharField(blank=True, null=True, max_length=800)
    threads_url = models.CharField(blank=True, null=True, max_length=800)
    blue_sky_url = models.CharField(blank=True, null=True, max_length=800)
    other_url = models.CharField(blank=True, null=True, max_length=800)

    # Bios
    wikipedia_url = models.CharField(blank=True, null=True, max_length=800)
    wikipedia_bio = models.TextField(null=True)
    statement_to_voters = models.TextField(null=True)
    statement_to_voters_last_updated = models.DateTimeField(null=True)

    # Background data from Nesta research
    place_of_birth = models.CharField(null=True, max_length=800)
    secondary_school = models.CharField(null=True, max_length=800)
    university_undergrad = models.CharField(null=True, max_length=800)
    field_undergrad = models.CharField(null=True, max_length=800)
    stem_undergrad = models.CharField(null=True, max_length=800)
    university_postgrad = models.CharField(null=True, max_length=800)
    field_postgrad = models.CharField(null=True, max_length=800)
    stem_postgrad = models.CharField(null=True, max_length=800)
    degree_cat = models.CharField(null=True, max_length=800)
    last_or_current_job = models.CharField(null=True, max_length=800)
    previously_in_parliament = models.CharField(null=True, max_length=800)

    # Meta
    delisted = models.BooleanField(default=False)

    objects = PersonManager()

    class Meta:
        get_latest_by = "last_updated"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.wikipedia_url:
            self.wikipedia_bio = None
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "person_view", args=[str(self.ynr_id), slugify(self.name)]
        )

    def has_biographical_info(self):
        attrs = [
            "place_of_birth",
            "secondary_school",
            "university_undergrad",
            "last_or_current_job",
        ]
        attr_count = 0
        for a in attrs:
            if getattr(self, a) is not None:
                attr_count += 1
        return attr_count > 1

    def get_ynr_url(self):
        return "{}/person/{}/".format(settings.YNR_BASE, self.ynr_id)

    @property
    def has_any_contact_info(self):
        """
        Does this person have any info to display in the contact info box?
        """
        return any(getattr(self, vt, False) for vt in VALUE_TYPES_TO_IMPORT)

    @property
    def has_social_media_account(self):
        """
        Do we have any social media accounts for this person?
        """
        social_media = [
            "twitter_username",
            "facebook_username",
            "instagram_username",
            "linkedin_url",
            "mastodon_username",
            "tiktok_url",
            "threads_url",
            "blue_sky_url",
        ]
        return any(getattr(self, sm, False) for sm in social_media)

    @property
    def get_max_facebook_ad_spend(self):
        return round(
            sum(
                [
                    float(x.get_spend_range[1])
                    for x in self.facebookadvert_set.all()
                ]
            )
        )

    @property
    def facebook_personal_username(self):
        facebook_personal_url = self.facebook_personal_url
        facebook_split = list(filter(None, facebook_personal_url.split("/")))
        return facebook_split[-1]

    @property
    def facebook_username(self):
        facebook_page_url = self.facebook_page_url
        facebook_split = list(filter(None, facebook_page_url.split("/")))
        return facebook_split[-1]

    @property
    def instagram_username(self):
        instagram_url = self.instagram_url
        instagram_split = list(filter(None, instagram_url.split("/")))
        return instagram_split[-1]

    @property
    def linkedin_username(self):
        return urlparse(self.linkedin_url.rstrip("/")).path.split("/")[-1]

    @property
    def youtube_username(self):
        youtube_url = self.youtube_profile
        if "channel" in youtube_url:
            return self.name + "'s Channel"
        youtube_split = list(filter(None, youtube_url.split("/")))
        return youtube_split[-1]

    @property
    def long_statement(self):
        return self.statement_count > 100

    @property
    def statement_count(self):
        statement = self.statement_to_voters
        return len(statement.split())

    @property
    def statement_intro(self):
        return self.statement_to_voters.split(".")[0] + "."

    @property
    def statement_remainder(self):
        statement_split = self.statement_to_voters.split(".")
        return ".".join(statement_split[1:])

    @cached_property
    def current_but_past_candidacies(self):
        """
        Returns a QuerySet of related PersonPost
        objects that are considered current but the
        election date has recently passed.
        """
        for candidacy in self.current_or_future_candidacies:
            if candidacy.election.in_past:
                return candidacy
        return None

    @cached_property
    def future_candidacies(self):
        """
        Returns a QuerySet of related PersonPost
        objects that are in the future.
        """
        return (
            self.personpost_set.future()
            .select_related("party", "post", "election", "post_election")
            .order_by("-election__election_date")
        )

    @cached_property
    def current_or_future_candidacies(self):
        """
        Returns a QuerySet of related PersonPost objects in the future
        """
        return (
            self.personpost_set.current_or_future()
            .select_related("party", "post", "election", "post_election")
            .order_by("-election__election_date")
        )

    @cached_property
    def past_not_current_candidacies(self):
        """
        Return a QuerySet of related PersonPost objects in the past and not
        current
        """
        return self.personpost_set.past_not_current().select_related(
            "party", "post", "election", "post_election"
        )

    @cached_property
    def featured_candidacy(self) -> PersonPost:
        """
        Return the current or future PersonPost object, or if there is not
        current/future, a past one. Some people will have more than one current
        candidacy but we still use this method to pull out some information
        (such as party name, manifestos, local parties) to use in the opening
        line of the persons intro, but we still show information for multiple
        candidacies in the intro by listing the elections they stand for (see
        _person_intro_card.html).
        """
        if not self.current_or_future_candidacies:
            return self.past_not_current_candidacies.first()

        return self.current_or_future_candidacies.first()

    @property
    def intro_template(self):
        """
        Return string path to intro template for this person.
        """
        base = "people/includes/intros/"
        if not self.featured_candidacy or not self.featured_candidacy.party:
            return f"{base}base.html"

        party = self.featured_candidacy.party
        ballot = self.featured_candidacy.post_election

        if party.is_independent and (ballot.is_mayoral or ballot.is_pcc):
            return f"{base}_independent_mayor_or_pcc.html"

        if party.is_independent:
            return f"{base}_independent.html"

        if party.party_name == "Speaker seeking re-election":
            return f"{base}_speaker.html"

        if ballot.is_parliamentary:
            return f"{base}_parl.html"

        if ballot.is_mayoral or ballot.is_pcc:
            return f"{base}_mayor_or_pcc.html"

        if ballot.election.uses_lists:
            return f"{base}_list_ballot.html"

        if ballot.is_constituency:
            return f"{base}_constituency.html"

        return f"{base}base.html"

    def get_verb(self):
        if self.death_date:
            return "was"
        if self.future_candidacies:
            return "is"
        return "was"

    @cached_property
    def intro(self):
        """
        Return a rendered string of the persons intro from a template.
        """
        verb = self.get_verb()

        context = {
            "verb": verb,
            "person": self,
            "person_name": self.name,
        }
        if self.featured_candidacy and self.featured_candidacy.party:
            context.update(
                {
                    "candidacy": self.featured_candidacy,
                    "party_name": self.featured_candidacy.party_name,
                    "list_position_ordinal": ordinal(
                        self.featured_candidacy.list_position
                    ),
                    "party_url": self.featured_candidacy.party.get_absolute_url(),
                    "post_label": self.featured_candidacy.post.label,
                    "post_url": self.featured_candidacy.post_election.get_absolute_url(),
                    "election_name": self.featured_candidacy.election.nice_election_name,
                    "election_url": self.featured_candidacy.election.get_absolute_url(),
                }
            )
        return render_to_string(
            template_name=self.intro_template, context=context
        )

    @property
    def text_intro(self):
        """
        Return intro without any HTML, special chars and extra whitespace
        """
        intro = self.intro
        intro = strip_tags(intro)
        intro = intro.strip()
        return " ".join(intro.split())

    @property
    def show_national_manifesto(self):
        """
        Return the national party manifesto for the featured candidacy
        """
        try:
            if (
                self.current_or_future_candidacies
                and self.featured_candidacy
                and self.national_party
                and (
                    self.featured_candidacy.party == self.national_party.parent
                )
                and self.manifestos
            ):
                return True
            return False
        except AttributeError:
            return False


class PersonRedirect(models.Model):
    old_person_id = models.IntegerField(db_index=True)
    new_person_id = models.IntegerField()
    ynr_created = models.DateTimeField()

    class Meta:
        get_latest_by = "ynr_created"
        unique_together = ("old_person_id", "new_person_id")


class AssociatedCompany(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    company_number = models.CharField(max_length=50)
    company_status = models.CharField(max_length=50)
    role = models.CharField(max_length=50)
    role_status = models.CharField(max_length=50, blank=True, null=True)
    role_appointed_date = models.DateField()
    role_resigned_date = models.DateField(blank=True, null=True)


class FacebookAdvert(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    ad_id = models.CharField(
        max_length=500, help_text="The Facebook ID for this advert"
    )
    ad_json = JSONField(
        help_text="The JSON returned from the Facebook "
        "Graph API for this advert"
    )
    image_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ("-ad_json__ad_delivery_start_time",)
        get_latest_by = "ad_json__ad_delivery_start_time"

    @property
    def get_spend_range(self):
        return sorted(self.ad_json.get("spend").values())
