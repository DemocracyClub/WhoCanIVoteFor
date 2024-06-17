from functools import cached_property
from typing import List

import requests
from administrations.constants import (
    ORG_ID_TO_MAYOR_NAME,
    POST_TYPE_TO_NAME,
    WEIGHT_MAP,
    PostTypes,
)
from core.utils import LastWord
from django.db.models.functions import Coalesce
from django.template.loader import select_template
from elections.models import PostElection


def get_weight(id_str, weight_map):
    # Split the ID by "::" and check each segment for a key in weight_map
    for part in id_str.split("::"):
        # If the part contains ":", split by ":" and check the first segment
        key = part.split(":")[0] if ":" in part else part

        if key in weight_map:
            return weight_map[key]

    # Return a default weight if no key is found
    return 0


class Administration:
    def __init__(self, admin_id: str):
        self.admin_id = admin_id
        data = self.load_json(admin_id)
        self.data = data
        self.post_type = PostTypes.from_administration_data(data)

    def load_json(self, administration_id):
        req = requests.get(
            f"https://s3.eu-west-2.amazonaws.com/ee.public.data/layers-of-state/administrations_json/{self.admin_id}.json"
        )
        return req.json()

    @property
    def administration_type(self):
        if self.admin_id.startswith("D::"):
            return "division"
        return "organisation"

    @property
    def role_type(self):
        return self.admin_id.split("::")[-1]

    def friendly_name(self):
        org_name = self.data["organisation"]["official_name"]

        if self.post_type in [PostTypes.GLA_A, PostTypes.GLA_C]:
            return "London Assembly"

        if self.post_type in [PostTypes.WAC, PostTypes.WAE]:
            return "Senedd Cymru"

        if self.post_type in [PostTypes.SPC, PostTypes.SPE]:
            return "Scottish Parliament"

        if self.administration_type == "organisation":
            if self.role_type == "mayor":
                if self.data["organisation"]["official_identifier"] == "london":
                    return "London Assembly"
                org_name = f"Mayor of {org_name}"

            return org_name
        div_name = self.data["division"]["name"]

        if self.role_type == "local":
            div_name = f"{div_name} ward"

        if self.role_type == "parl":
            return f"{div_name} parliamentary constituency"
        return f"{org_name}: {div_name}"

    def role_name(self):
        name = None

        index = 0
        if self.seats_total > 1:
            index = -1
        if self.post_type in [PostTypes.GLA_A, PostTypes.SPE]:
            index = -1
        role_name = POST_TYPE_TO_NAME.get(self.post_type, [name])[index]

        if self.post_type == PostTypes.MAYOR:
            org_id = self.data["organisation"]["official_identifier"]
            if org_id in ORG_ID_TO_MAYOR_NAME:
                return ORG_ID_TO_MAYOR_NAME[org_id]

        if self.post_type in [
            PostTypes.GLA_C,
            PostTypes.WAC,
            PostTypes.WAE,
            PostTypes.SPE,
            PostTypes.SPC,
        ]:
            role_name = f"{role_name} for {self.data['division']['name']}"

        return role_name

    @cached_property
    def seats_total(self):
        if "division" in self.data:
            return self.data["division"]["seats_total"]

        return 1

    def responsibilities_template(self):
        return select_template(
            [
                f"responsibilities/single_id/{self.admin_id}.html",
                f"responsibilities/post_type/{self.post_type.name}.html",
                f"responsibilities/org_id/{self.data['organisation']['official_identifier']}.html",
                f"responsibilities/org_type/{self.data['organisation']['organisation_type']}.html",
            ]
        )

    def should_show_people(self):
        if self.post_type == PostTypes.GLA_A:
            return True

        if self.seats_total == 1:
            return True

        if self.ballot_obj.winner_count == self.seats_total:
            return True

        return False

    @cached_property
    def ballot_obj(self):
        ballot_id = self.data.get(
            "last_division_election_id",
            self.data.get(
                "last_org_election_id",
            ),
        )

        if self.post_type == PostTypes.GLA_A:
            date = ballot_id.split(".")[-1]
            ballot_id = f"gla.a.{date}"

        return PostElection.objects.get(ballot_paper_id=ballot_id)

    @cached_property
    def elected_people(self):
        if not self.should_show_people:
            return None

        qs = self.ballot_obj.personpost_set.filter(elected=True).select_related(
            "party", "person"
        )
        return (
            qs.annotate(last_name=LastWord("person__name"))
            .annotate(
                name_for_ordering=Coalesce("person__sort_name", "last_name")
            )
            .order_by("name_for_ordering", "person__name")
        )

    @cached_property
    def weight(self):
        weight_modifier = 0

        org_type = self.data["organisation"]["organisation_type"]
        if self.admin_id == "O::london::mayor":
            org_type = "gla"
        if self.role_type == "mayor":
            weight_modifier = -10

        if self.post_type in [PostTypes.GLA_A, PostTypes.WAE, PostTypes.SPE]:
            weight_modifier = 10
        weight = WEIGHT_MAP.get(org_type, 1)
        return weight + weight_modifier


class AdministrationsHelper:
    def __init__(self, postcode: str):
        self.postcode = postcode
        self.administration_ids = self.lookup_administration_ids(self.postcode)
        self.administrations: List[Administration] = []
        IGNORE_IDS = [
            "O::LIV::mayor",
            "O::TOB::mayor",
            "O::BST::mayor",
        ]
        for admin_id in self.administration_ids:
            if admin_id in IGNORE_IDS:
                continue
            self.administrations.append(Administration(admin_id))

        self.administrations = sorted(
            self.administrations, key=lambda admin: admin.weight
        )

    def lookup_administration_ids(self, postcode):
        if postcode == "GL5 1NA":
            return [
                "D::GLS::2021-05-06::unit_id:42821::local",
                "D::STO::2016-04-13::gss:E05010988::local",
                "D::parl-hoc::2024-07-04::gss:E14001529::parl",
                "O::gloucestershire::pcc",
            ]
        if postcode == "DG8 8NH":
            return [
                "D::DGY::2017-05-04::gss:S13002881::local",
                "D::parl-hoc::2024-07-04::gss:S14000073::parl",
                "D::sp::2016-04-13::gss:S16000114::sp::c",
                "D::sp::2016-04-13::gss:S17000015::sp::r",
            ]
        if postcode == "SE22 8DJ":
            return [
                "D::SWK::2018-05-03::gss:E05011097::local",
                "D::gla::2004-12-02::gss:E32000010::gla::c",
                "D::parl-hoc::2024-07-04::gss:E14001205::parl",
                "O::gla::gla::a",
                "O::london::mayor",
            ]

        return []
        # TODO: clean up
        # req = requests.get(
        #     f"http://localhost:3000/rpc/get_identifiers_by_postcode?postcode={postcode}"
        # )
        # ids = []
        #
        # for obj in req.json():
        #     ids.append(obj["identifier"])
        # return ids
