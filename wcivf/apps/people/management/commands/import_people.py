import os
import json
import tempfile
import shutil
from datetime import timedelta
from urllib.parse import urlencode

from dateutil.parser import parse

from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

import requests

from core.helpers import show_data_on_error
from elections.import_helpers import YNRBallotImporter
from people.models import Person
from elections.models import PostElection


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--recent",
            action="store_true",
            dest="recent",
            default=False,
            help="Import changes in the last `n` minutes",
        )

        parser.add_argument(
            "--since",
            action="store",
            dest="since",
            type=self.valid_date,
            help="Import changes since [datetime]",
        )
        parser.add_argument(
            "--update-info-only",
            action="store_true",
            help="Only update person info, not posts",
        )

    def valid_date(self, value):
        return parse(value)

    def handle(self, **options):
        self.options = options
        self.dirpath = tempfile.mkdtemp()
        self.ballot_importer = YNRBallotImporter(stdout=self.stdout)

        try:
            last_updated = Person.objects.latest().last_updated
            self.past_time_str = last_updated - timedelta(hours=1)
        except Person.DoesNotExist:
            # In case this is the first run
            self.past_time_str = "1800-01-01"
        if self.options["since"]:
            self.past_time_str = self.options["since"]

        self.past_time_str = str(self.past_time_str)

        try:
            self.download_pages()
            self.add_to_db()
        finally:
            self.delete_merged_people()
            shutil.rmtree(self.dirpath)

    def add_to_db(self):
        self.existing_people = set(Person.objects.values_list("pk", flat=True))
        self.seen_people = set()

        files = [f for f in os.listdir(self.dirpath) if f.endswith(".json")]
        files = sorted(files, key=lambda k: int(k.split("-")[-1].split(".")[0]))
        for file in files:
            self.stdout.write("Importing {}".format(file))
            with open(os.path.join(self.dirpath, file), "r") as f:
                results = json.loads(f.read())
                self.add_people(
                    results, update_info_only=self.options["update_info_only"]
                )

        should_clean_up = not any(
            [
                self.options["recent"],
                self.options["update_info_only"],
                self.options["since"],
            ]
        )
        if should_clean_up:
            deleted_ids = self.existing_people.difference(self.seen_people)
            Person.objects.filter(ynr_id__in=deleted_ids).delete()

    def save_page(self, url, page):
        # get the file name from the page number
        if "cached-api" in url:
            filename = url.split("/")[-1]
        else:
            if "page=" in url:
                page_number = url.split("page=")[1].split("&")[0]

            else:
                page_number = 1
            filename = "page-{}.json".format(page_number)
        file_path = os.path.join(self.dirpath, filename)

        # Save the page
        with open(file_path, "w") as f:
            f.write(page)

    def download_pages(self):
        params = {"page_size": "200"}
        if self.options["recent"] or self.options["since"]:
            params["updated_gte"] = self.past_time_str

            next_page = settings.YNR_BASE + "/api/next/people/?{}".format(
                urlencode(params)
            )
        else:
            next_page = (
                settings.YNR_BASE
                + "/media/cached-api/latest/people-000001.json"
            )

        while next_page:
            self.stdout.write("Downloading {}".format(next_page))
            req = requests.get(next_page)
            req.raise_for_status()
            page = req.text
            results = req.json()
            self.save_page(next_page, page)
            next_page = results.get("next")

    @transaction.atomic
    def add_people(self, results, update_info_only=False):
        for person in results["results"]:
            with show_data_on_error("Person {}".format(person["id"]), person):
                person_obj = Person.objects.update_or_create_from_ynr(
                    person, update_info_only=update_info_only
                )

                if self.options["recent"]:
                    self.update_candidacies(person, person_obj)

                if person["candidacies"]:
                    self.seen_people.add(person_obj.pk)

    def update_candidacies(self, person, person_obj):
        """
        Compare the API dict to the candidacies we know about
        """
        known_candidacies = set(
            person_obj.personpost_set.all().values_list(
                "post_election__ballot_paper_id", flat=True
            )
        )

        remote_candidacies = set(
            [c["ballot"]["ballot_paper_id"] for c in person["candidacies"]]
        )

        if remote_candidacies != known_candidacies:
            # Delete any old candidacies
            deleted_candidacies = known_candidacies - remote_candidacies
            person_obj.personpost_set.filter(
                post_election__ballot_paper_id__in=deleted_candidacies
            ).delete()

            added_candidacies = remote_candidacies - known_candidacies
            for candidacy in added_candidacies:
                try:
                    ballot = PostElection.objects.get(ballot_paper_id=candidacy)
                except PostElection.DoesNotExist:
                    # This might be because we've not run import_ballots
                    # recently enough. Let's import just the ballots for this
                    # date
                    self.import_ballots_for_date(candidacy.split(".")[-1])
                    ballot = PostElection.objects.get(ballot_paper_id=candidacy)
                for candidacy_dict in person["candidacies"]:
                    if candidacy_dict["ballot"]["ballot_paper_id"] == candidacy:
                        candidacy_dict_for_ballot = candidacy_dict

                person_obj.personpost_set.update_or_create(
                    post_election=ballot,
                    post=ballot.post,
                    election=ballot.election,
                    party_id=candidacy_dict_for_ballot["party"]["legacy_slug"],
                    list_position=candidacy_dict_for_ballot[
                        "party_list_position"
                    ],
                    elected=candidacy_dict_for_ballot["elected"],
                )

    def import_ballots_for_date(self, date):
        self.ballot_importer.do_import(params={"election_date": date})

    def delete_merged_people(self):
        url = (
            settings.YNR_BASE
            + "/api/next/person_redirects/?page_size=200&updated_gte={}".format(
                self.past_time_str
            )
        )
        merged_ids = []
        while url:
            req = requests.get(url)
            page = req.json()
            for result in page["results"]:
                merged_ids.append(result["old_person_id"])
            url = page.get("next")
        Person.objects.filter(ynr_id__in=merged_ids).delete()
