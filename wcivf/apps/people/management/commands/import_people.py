import json
import os
import shutil
import tempfile
from urllib.parse import urlencode

import requests
from core.helpers import show_data_on_error
from dateutil.parser import parse
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from elections.import_helpers import YNRBallotImporter
from elections.models import PostElection
from parties.models import Party
from people.models import Person, PersonRedirect

from wcivf.apps.elections.import_helpers import time_function_length
from wcivf.apps.people.import_helpers import YNRPersonImporter


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--recently-updated",
            action="store_true",
            dest="recently_updated",
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
            "--exclude-candidacies",
            action="store_true",
            dest="exclude_candidacies",
            default=False,
            help="Ignore candidacies when importing people",
        )

    def valid_date(self, value):
        return parse(value)

    def handle(self, **options):
        self.options = options
        self.ballot_importer = YNRBallotImporter(stdout=self.stdout)
        self.updated_ballots = set()  # Track ballots that need rank calculation

        try:
            person = Person.objects.latest()
            self.stdout.write(
                f"Using timestamp from {person.name} (PK:{person.pk} TS:{person.last_updated})"
            )
            last_updated = person.last_updated
            self.past_time_str = str(last_updated)
        except Person.DoesNotExist:
            # In case this is the first run
            self.past_time_str = "1800-01-01"
        if self.options["since"]:
            self.past_time_str = self.options["since"]

        self.past_time_str = str(self.past_time_str)

        if options["recently_updated"]:
            importer = YNRPersonImporter(params={"last_updated": last_updated})
            for page in importer.people_to_import:
                self.add_people(results=page)

        else:
            self.dirpath = tempfile.mkdtemp()
            self.download_pages()
            self.add_to_db()
            shutil.rmtree(self.dirpath)

        self.delete_merged_people()
        self.delete_orphaned_people()
        self.calculate_ranks_for_updated_ballots()

    def add_to_db(self):
        self.existing_people = set(Person.objects.values_list("pk", flat=True))
        self.seen_people = set()

        files = [f for f in os.listdir(self.dirpath) if f.endswith(".json")]
        files = sorted(files, key=lambda k: int(k.split("-")[-1].split(".")[0]))
        for file in files:
            self.stdout.write("Importing {}".format(file))
            with open(os.path.join(self.dirpath, file), "r") as f:
                results = json.loads(f.read())
                self.add_people(results)

        # Calculate ranks after all people have been processed
        self.calculate_ranks_for_updated_ballots()

        should_clean_up = not any(
            [
                self.options["recently_updated"],
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
        if self.options["recently_updated"] or self.options["since"]:
            params["last_updated"] = self.past_time_str

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

    @time_function_length
    @transaction.atomic
    def add_people(self, results):
        self.stdout.write(f"Found {results['count']} people to import")
        for person in results["results"]:
            with show_data_on_error("Person {}".format(person["id"]), person):
                person_obj = Person.objects.update_or_create_from_ynr(person)
                self.stdout.write(
                    f"Updated {person_obj.name} ({person_obj.pk})"
                )

                if self.options["recently_updated"]:
                    self.delete_old_candidacies(
                        person_data=person,
                        person_obj=person_obj,
                    )
                    if not self.options["exclude_candidacies"]:
                        self.update_candidacies(
                            person_data=person, person_obj=person_obj
                        )
                    # dont keep track of seen people in a recent update
                    continue

                if person["candidacies"]:
                    self.seen_people.add(person_obj.pk)

    def delete_old_candidacies(self, person_data, person_obj):
        """
        Delete any candidacies that have been deleted upstream in YNR
        """
        ballot_paper_ids = [
            c["ballot"]["ballot_paper_id"] for c in person_data["candidacies"]
        ]

        count, _ = person_obj.personpost_set.exclude(
            post_election__ballot_paper_id__in=ballot_paper_ids
        ).delete()
        self.stdout.write(f"Deleted {count} candidacies for {person_obj.name}")

    def update_candidacies(self, person_data, person_obj):
        """
        Loops through candidacy dictionaries in the person data and updates or
        creates the candidacy object for the Person
        """
        for candidacy in person_data["candidacies"]:
            ballot_paper_id = candidacy["ballot"]["ballot_paper_id"]
            try:
                ballot = PostElection.objects.get(
                    ballot_paper_id=ballot_paper_id
                )
            except PostElection.DoesNotExist:
                # This might be because we've not run import_ballots
                # recently enough. Let's import just the ballots for this
                # date
                date = ballot_paper_id.split(".")[-1]
                self.import_ballots_for_date(date=date)
                ballot = PostElection.objects.get(
                    ballot_paper_id=ballot_paper_id
                )

            # TODO check if the post/election could have changed and should be
            # used in defaults dict
            defaults = {
                "party_id": candidacy["party"]["legacy_slug"],
                "list_position": candidacy["party_list_position"],
                "deselected": candidacy["deselected"],
                "deselected_source": candidacy["deselected_source"],
                "elected": candidacy["elected"],
                "party_name": candidacy["party_name"],
                "party_description_text": candidacy["party_description_text"],
            }
            # TODO add this to YNR CandidacyOnPersonSerializer
            if candidacy.get("result"):
                num_ballots = candidacy["result"].get("num_ballots", None)
                defaults["votes_cast"] = num_ballots

            personpost, created = person_obj.personpost_set.update_or_create(
                post_election=ballot,
                post=ballot.post,
                election=ballot.election,
                defaults=defaults,
            )
            for party in candidacy.get("previous_party_affiliations", []):
                # if the previous party affiliation is the same as the
                # party on the candidacy skip it
                party_id = party["legacy_slug"]
                if party_id == personpost.party_id:
                    continue

                try:
                    party = Party.objects.get(party_id=party["legacy_slug"])
                except Party.DoesNotExist:
                    continue
                personpost.previous_party_affiliations.add(party)

            msg = f"{personpost} was {'created' if created else 'updated'}"
            self.stdout.write(msg=msg)

            # Track ballot for rank calculation if it has results
            if (
                candidacy.get("result")
                and candidacy["result"].get("num_ballots") is not None
            ):
                self.updated_ballots.add(ballot)

    def import_ballots_for_date(self, date):
        self.ballot_importer.do_import(params={"election_date": date})

    def calculate_ranks_for_updated_ballots(self):
        """Calculate ranks for all ballots that had vote counts updated."""
        if not self.updated_ballots:
            return

        for ballot in self.updated_ballots:
            self.stdout.write(f"Calculating ranks for {ballot.ballot_paper_id}")
            ballot.update_candidate_ranks()

        self.stdout.write(
            f"Calculated ranks for {len(self.updated_ballots)} ballots"
        )

    @time_function_length
    def delete_merged_people(self):
        latest_person_redirect = PersonRedirect.objects.latest().ynr_created
        url = f"{settings.YNR_BASE}/api/next/person_redirects/?page_size=200&created={latest_person_redirect}"
        if settings.YNR_API_KEY:
            url = f"{url}&auth_token={settings.YNR_API_KEY}"
        merged_ids = []
        while url:
            resp = requests.get(url)
            resp.raise_for_status()
            page = resp.json()
            for result in page.get("results", []):
                merged_ids.append(result["old_person_id"])
                PersonRedirect.objects.get_or_create(
                    old_person_id=result["old_person_id"],
                    new_person_id=result["new_person_id"],
                    ynr_created=result["created"],
                )
            url = page.get("next")
        Person.objects.filter(ynr_id__in=merged_ids).delete()

    @time_function_length
    def delete_orphaned_people(self):
        """
        Delete all people without candidacies
        """
        _, deleted_dict = Person.objects.filter(
            personpost__isnull=True
        ).delete()
        count = deleted_dict.get("people.Person", 0)
        self.stdout.write(f"Deleted {count} orphaned People objects")
