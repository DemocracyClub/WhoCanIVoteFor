from django.contrib.humanize.templatetags.humanize import ordinal, intcomma
from django.db.models import JSONField
from django.urls import reverse
from django.db import models
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.text import slugify
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from elections.models import Election, Post
from parties.models import Party

from wcivf import settings
from .managers import PersonPostManager, PersonManager, VALUE_TYPES_TO_IMPORT


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

    objects = PersonPostManager()

    def __str__(self):
        return "{} ({}, {})".format(
            self.person.name, self.post.label, self.election.slug
        )

    def get_local_party(self):
        qs = self.party.local_parties.filter(post_election=self.post_election)
        if qs.exists:
            return qs.get()
        else:
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

    # Bios
    wikipedia_url = models.CharField(blank=True, null=True, max_length=800)
    wikipedia_bio = models.TextField(null=True)
    statement_to_voters = models.TextField(null=True)

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

    objects = PersonManager()

    class Meta:
        get_latest_by = "last_updated"

    def __str__(self):
        return self.name

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
    def should_show_email_cta(self):
        show_cta = bool(self.email)

        conditions = [self.statement_to_voters]

        all_conditions = not any(map(bool, conditions))

        return all([show_cta, all_conditions])

    @property
    def has_any_contact_info(self):
        """
        Does this person have any info to display in the contact info box?
        """
        return any([getattr(self, vt, False) for vt in VALUE_TYPES_TO_IMPORT])

    @property
    def cta_example_details(self):
        attrs = (
            ("cv", "CV"),
            ("statement_to_voters", "statement to voters"),
            ("email", "email"),
            ("homepage_url", "homepage"),
            ("twitter_username", "twitter account"),
        )
        return [a[1] for a in attrs if not getattr(self, a[0], False)]

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
        facebook_personal_username = facebook_split[-1]

        return facebook_personal_username

    @property
    def facebook_username(self):
        facebook_page_url = self.facebook_page_url
        facebook_split = list(filter(None, facebook_page_url.split("/")))
        return facebook_split[-1]

    @property
    def instagram_username(self):
        instagram_url = self.instagram_url
        instagram_split = list(filter(None, instagram_url.split("/")))
        instagram_username = instagram_split[-1]

        return instagram_username

    @property
    def linkedin_username(self):
        linkedin_url = self.linkedin_url
        linkedin_split = list(filter(None, linkedin_url.split("/")))
        linkedin_username = linkedin_split[-1]

        return linkedin_username

    @property
    def youtube_username(self):
        youtube_url = self.youtube_profile
        if "channel" in youtube_url:
            return self.name + "'s Channel"
        youtube_split = list(filter(None, youtube_url.split("/")))
        youtube_username = youtube_split[-1]
        return youtube_username

    @property
    def long_statement(self):
        return self.statement_count > 100

    @property
    def statement_count(self):
        statement = self.statement_to_voters
        statement_count = len(statement.split())
        return statement_count

    @property
    def statement_intro(self):
        statement_intro = self.statement_to_voters.split(".")[0] + "."
        return statement_intro

    @property
    def statement_remainder(self):
        statement_split = self.statement_to_voters.split(".")
        statement_remainder = ".".join(statement_split[1:])

        return statement_remainder

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

        if party.is_independent:
            return f"{base}_independent.html"

        if party.party_name == "Speaker seeking re-election":
            return f"{base}_speaker.html"

        if ballot.is_parliamentary:
            return f"{base}_parl.html"

        if ballot.is_mayoral:
            return f"{base}_mayor.html"

        if ballot.is_pcc:
            return f"{base}_pcc.html"

        if ballot.is_constituency:
            return f"{base}_constituency.html"

        if ballot.election.uses_lists:
            return f"{base}_list_ballot.html"

        return f"{base}base.html"

    @cached_property
    def intro(self):
        """
        Return a rendered string of the persons intro from a template.
        """
        verb = "was"
        if self.current_or_future_candidacies and not self.death_date:
            verb = "is"

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
