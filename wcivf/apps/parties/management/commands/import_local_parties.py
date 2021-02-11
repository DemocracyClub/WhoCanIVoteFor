from dateutil.parser import parse

from django.core.management.base import BaseCommand
from django.db import transaction

import csv

from parties.models import Party, LocalParty
from elections.models import PostElection


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "filename", help="Path to the file with the local parties"
        )
        parser.add_argument(
            "--election-date",
            action="store",
            type=self.valid_date,
            help="The date of elections this file has data about",
        )

    def valid_date(self, value):
        return parse(value)

    def get_party_list_from_party_id(self, party_id):
        party_id = "party:{}".format(party_id)

        PARTIES = [["party:53", "party:84", "joint-party:53-119"]]

        for party_list in PARTIES:
            if party_id in party_list:
                return party_list
        return [party_id]

    @transaction.atomic
    def handle(self, **options):
        # Delete all data from non-current elections first,
        # as rows in the source might have been deleted
        LocalParty.objects.filter(
            post_election__election__election_date=options["election_date"]
        ).delete()

        with open(options["filename"], "r") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    party_id = row["party_id"].strip()
                except AttributeError:
                    # catch when party_id is None
                    continue

                # Try to get a post election
                try:
                    party_list = self.get_party_list_from_party_id(party_id)
                    parties = Party.objects.filter(party_id__in=party_list)
                except Party.DoesNotExist:
                    print("Parent party not found with ID %s" % party_id)
                    continue

                post_elections = PostElection.objects.filter(
                    ballot_paper_id=row["election_id"]
                )

                if not post_elections.exists():
                    # This might be an election ID, in that case,
                    # apply thie row to all post elections without
                    # info already
                    post_elections = PostElection.objects.filter(
                        election__slug=row["election_id"]
                    ).exclude(localparty__parent__in=parties)
                for party in parties:
                    self.add_local_party(row, party, post_elections)

    def add_local_party(self, row, party, post_elections):
        twitter = row["Twitter"].replace("https://twitter.com/", "")
        twitter = twitter.split("/")[0]
        twitter = twitter.split("?")[0]
        for post_election in post_elections:
            LocalParty.objects.update_or_create(
                parent=party,
                post_election=post_election,
                defaults={
                    "name": row["Local party name"],
                    "twitter": twitter,
                    "facebook_page": row["Facebook"],
                    "homepage": row["Website"],
                    "email": row["Email"],
                },
            )
