from django.core.management.base import BaseCommand

import csv

from parties.models import Party, Manifesto
from elections.models import Election


class Command(BaseCommand):
    """
    The 2017 party manifesto list is at:
    https://docs.google.com/spreadsheets/d/1ag0FuUqUOJlP8nvVVxjxFh_2HDNH6WJ9srZSJh9KG_c/edit#gid=816418254
    Download and store it locally, then run this command with:
    manage.py import_manifestos /path/to/csv
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "filename", help="Path to the file with the manifestos"
        )

    def handle(self, **options):
        with open(options["filename"], "r") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                party_id = row["party_id"].strip()
                if "-" in party_id:
                    party_id = "joint-party:" + party_id
                else:
                    party_id = "party:" + party_id

                try:
                    election = Election.objects.get(slug=row["election_id"])
                except:
                    continue
                try:
                    party = Party.objects.get(party_id="%s" % party_id)
                    self.add_manifesto(row, party, election)
                except Party.DoesNotExist:
                    print("Party not found with ID %s" % party_id)

    def add_manifesto(self, row, party, election):
        country = row.get("country", "UK").strip()
        if "local." in election.slug:
            country = "Local"
        language = row.get("language", "English").strip()

        manifesto_web = row["manifesto website"].strip()
        manifesto_pdf = row["manifesto pdf"].strip()
        easy_read_url = row.get("easy read version", "").strip()
        if any([manifesto_web, manifesto_pdf]):
            manifesto_obj, created = Manifesto.objects.update_or_create(
                election=election,
                party=party,
                country=country,
                language=language,
                defaults={
                    "web_url": manifesto_web,
                    "pdf_url": manifesto_pdf,
                    "easy_read_url": easy_read_url,
                },
            )
            manifesto_obj.save()
