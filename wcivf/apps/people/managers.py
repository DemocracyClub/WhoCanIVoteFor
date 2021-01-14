import requests
from django.conf import settings

from django.db import models
from django.db.models import Count
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

VALUE_TYPES_TO_IMPORT = [
    "twitter_username",
    "facebook_page_url",
    "facebook_personal_url",
    "linkedin_url",
    "homepage_url",
    "party_ppc_page_url",
    "wikipedia_url",
    "theyworkforyou",
    "youtube_profile",
    "instagram_url",
]


class PersonPostQuerySet(models.QuerySet):
    def by_party(self):
        return self.order_by("party__party_name", "list_position")

    def elected(self):
        return self.filter(elected=True)

    def counts_by_post(self):
        return (
            self.values(
                "post__label",
                "post_id",
                "election__slug",
                "election__name",
                "post_election__cancelled",
            )
            .annotate(num_candidates=Count("person"))
            .order_by("-election__election_date", "post__label")
        )

    def current_or_future(self):
        """
        Return objects where election is marked as current or election is in the future
        """
        return self.filter(
            models.Q(election__election_date__gte=now())
            | models.Q(election__current=True)
        )

    def past_not_current(self):
        """
        Return objects where related election is not marked as current, in the past, and was not cancelled
        """
        return self.filter(
            election__current=False,
            post_election__cancelled=False,
            election__election_date__lt=now(),
        )

    def current(self):
        """
        Return objects where related election is marked as current
        """
        return self.filter(election__current=True)


class PersonPostManager(models.Manager):
    def get_queryset(self):
        return PersonPostQuerySet(self.model, using=self._db)

    def by_party(self):
        return self.get_queryset().by_party()

    def elected(self):
        return self.get_queryset().elected()

    def counts_by_post(self):
        return self.get_queryset().counts_by_post()

    def current_or_future(self):
        return self.get_queryset().current_or_future()

    def past_not_current(self):
        return self.get_queryset().past_not_current()

    def current(self):
        return self.get_queryset().current()


class PersonManager(models.Manager):
    def update_or_create_from_ynr(self, person, update_info_only=False):

        last_updated = parse_datetime(person["last_updated"])

        sort_name = person.get("sort_name")
        if not sort_name:
            sort_name = person["name"].split(" ")[-1]

        defaults = {
            "name": person["name"],
            "sort_name": sort_name,
            "email": person["email"] or None,
            "gender": person["gender"] or None,
            "birth_date": person["birth_date"] or None,
            "death_date": person["death_date"] or None,
            "last_updated": last_updated,
        }

        for value_type in VALUE_TYPES_TO_IMPORT:
            defaults[value_type] = None
        del defaults["theyworkforyou"]

        for identifier in person["identifiers"]:
            value_type = identifier["value_type"]

            if value_type in VALUE_TYPES_TO_IMPORT:
                if value_type == "theyworkforyou":
                    defaults["twfy_id"] = identifier[
                        "internal_identifier"
                    ].replace("uk.org.publicwhip/person/", "")
                else:
                    defaults[value_type] = identifier["value"]

        defaults["statement_to_voters"] = person["statement_to_voters"]
        defaults["favourite_biscuit"] = person["favourite_biscuit"]

        if "thumbnail" in person:
            defaults["photo_url"] = person["thumbnail"]

        person_id = person["id"]
        person_obj, _ = self.update_or_create(
            ynr_id=person_id, defaults=defaults
        )
        return person_obj

    def get_by_pk_or_redirect_from_ynr(self, pk):
        try:
            return self.get(pk=pk)
        except self.model.DoesNotExist:
            req = requests.get(
                "{}/api/next/person_redirects/{}/".format(settings.YNR_BASE, pk)
            )
            if req.status_code == 200:
                return self.get(pk=req.json()["new_person_id"])
            raise
