from django.core.management.base import BaseCommand
from django.conf import settings

import requests

from parties.models import Party


class Command(BaseCommand):
    def handle(self, **options):

        next_page = settings.YNR_BASE + "/api/next/parties/?page_size=200"
        while next_page:
            req = requests.get(next_page)
            results = req.json()
            self.add_parties(results)
            next_page = results.get("next")

    def add_party_descriptions(self, party_obj, descriptions):
        for description in descriptions:
            party_obj.party_descriptions.update_or_create(
                party=party_obj,
                description=description["description"],
                defaults={
                    "date_description_approved": description[
                        "date_description_approved"
                    ],
                    "active": description["active"],
                },
            )

    def add_party_emblems(self, party_obj, emblems):
        for emblem in emblems:
            party_obj.emblems.update_or_create(
                party=party_obj,
                ec_emblem_id=emblem["ec_emblem_id"],
                defaults={
                    "emblem_url": emblem["image"],
                    "description": emblem["description"],
                    "date_approved": emblem["date_approved"],
                    "default": emblem["default"],
                    "active": emblem["active"],
                },
            )

    def add_parties(self, results):
        for party in results["results"]:
            party_obj, created = Party.objects.update_or_create_from_ynr(party)
            if created:
                print("Added new party: {0}".format(party["name"]))

            self.add_party_descriptions(party_obj, party["descriptions"])
            self.add_party_emblems(party_obj, party["emblems"])
