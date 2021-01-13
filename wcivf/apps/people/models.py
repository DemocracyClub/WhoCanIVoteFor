from django.contrib.postgres.fields import JSONField
from django.urls import reverse
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
from django.utils.functional import cached_property
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
    election = models.ForeignKey(Election, null=False, on_delete=models.CASCADE)
    list_position = models.IntegerField(blank=True, null=True)
    elected = models.NullBooleanField()
    votes_cast = models.PositiveIntegerField(null=True)
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
    last_updated = models.DateTimeField(default=now)

    # contact points
    twitter_username = models.CharField(blank=True, null=True, max_length=100)
    facebook_page_url = models.CharField(blank=True, null=True, max_length=800)
    facebook_personal_url = models.CharField(
        blank=True, null=True, max_length=800
    )
    linkedin_url = models.CharField(blank=True, null=True, max_length=800)
    homepage_url = models.CharField(blank=True, null=True, max_length=800)
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

    @cached_property
    def current_candidacies(self):
        """
        Returns a QS of related PersonPost objects in the future
        """
        return self.personpost_set.future().select_related(
            "party", "post", "election", "post_election"
        )

    @cached_property
    def past_candidacies(self):
        return self.personpost_set.past().select_related(
            "party", "post", "election", "post_election"
        )


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
