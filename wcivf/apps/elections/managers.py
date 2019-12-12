from django.db import models
from django.utils import timezone
from .helpers import EEHelper


class ElectionQuerySet(models.QuerySet):
    def current(self):
        return self.filter(current=True)

    def future(self):
        return self.filter(election_date__gt=timezone.now())

    def current_or_future(self):
        return self.filter(
            models.Q(current=True) | models.Q(election_date__gt=timezone.now())
        )


class ElectionManager(models.Manager.from_queryset(ElectionQuerySet)):
    def get_explainer(self, election):
        ee = EEHelper()
        ee_data = ee.get_data(election["id"])
        if ee_data:
            description = ee_data["explanation"]
            if description:
                return description
        return election["description"]

    def update_or_create_from_ynr(self, election):
        election_type = self.election_id_to_type(election["id"])

        election_weight = 10
        if election["party_lists_in_use"]:
            election_weight = 20
        if election_type == "mayor":
            election_weight = 5

        description = self.get_explainer(election)

        return self.update_or_create(
            slug=election["id"],
            defaults={
                "election_date": election["election_date"],
                "name": election["name"].replace("2016", "").strip(),
                "current": election["current"],
                "description": description,
                "election_type": election_type,
                "uses_lists": election["party_lists_in_use"],
                "for_post_role": election["for_post_role"],
                "election_weight": election_weight,
            },
        )

    def election_id_to_type(self, election_id):
        parts = election_id.split(".")
        return parts[0]


class PostManager(models.Manager):
    def update_or_create_from_ynr(self, post_dict):
        from .models import Election, PostElection

        post, created = self.update_or_create(
            ynr_id=post_dict["id"],
            defaults={
                "label": post_dict["label"],
                "role": post_dict["role"],
                "group": post_dict["group"],
                "organization": post_dict["organization"]["name"],
                "area_name": post_dict["label"],
                "area_id": post_dict["id"],
            },
        )

        for election_dict in post_dict["elections"]:
            election = Election.objects.get(slug=election_dict["id"])
            kwargs = {"election": election, "post": post}

            kwargs["locked"] = election_dict.get("candidates_locked", False)
            if kwargs["locked"]:
                if election_dict["winner_count"] == len(
                    post_dict["memberships"]
                ):
                    kwargs["contested"] = False
                kwargs["winner_count"] = election_dict["winner_count"]

            kwargs["cancelled"] = election_dict["cancelled"]
            PostElection.objects.update_or_create(
                ballot_paper_id=election_dict["ballot_paper_id"],
                defaults=kwargs,
            )

        return (post, created)
