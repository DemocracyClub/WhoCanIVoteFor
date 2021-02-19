from collections import namedtuple
from dateutil.parser import parse

from django.core.management.base import BaseCommand
from django.db import transaction

from core.mixins import ReadFromUrlMixin
from core.helpers import twitter_username
from parties.models import Party, LocalParty
from parties.importers import LocalPartyImporter
from elections.models import Election, PostElection


LocalElection = namedtuple("LocalElection", ["date", "urls"])


class Command(ReadFromUrlMixin, BaseCommand):
    ELECTIONS = [
        LocalElection(
            date="2018-05-03",
            urls=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vS3pC0vtT9WaCyKDzqARQZY6aoYCyKZLyIvumKaX3TpqG0rt4y0fXp6dOPOZGMX6v0dFczHfizwidwZ/pub?gid=582783400&single=true&output=csv",
            ],
        ),
        LocalElection(
            date="2019-05-02",
            urls=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTO-z37bBMxKwCuORIl2vE8v0kMFHlHETvBhGjuDidM1Wy4QxQawRou53kNLjEiJmpMhebRqoWZL9s-/pub?gid=0&single=true&output=csv",
            ],
        ),
        LocalElection(
            date="2021-05-06",
            urls=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1210343217&single=true&output=csv",
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=2091491905&single=true&output=csv",
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1013163356&single=true&output=csv",
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1273833263&single=true&output=csv",
            ],
        ),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-update",
            "-f",
            action="store_true",
            help="The date of elections this file has data about",
        )

    def valid_date(self, value):
        return parse(value)

    def delete_current_data(self, election):
        count, _ = LocalParty.objects.filter(
            post_election__election__election_date=election.date,
        ).delete()
        self.stdout.write(f"Deleted {count} old objects")

    def current_elections(self, election):
        if self.force_update:
            return True
        return Election.objects.filter(
            current=True, election_date=election.date
        ).exists()

    @transaction.atomic
    def handle(self, **options):
        self.force_update = options["force_update"]

        for election in self.ELECTIONS:
            self.delete_current_data(election=election)

            if not self.current_elections(election=election):
                self.stdout.write(
                    f"No current elections for {election.date}, skipping"
                )
                continue

            for url in election.urls:
                importer = LocalPartyImporter(url=url)
                importer.add_parties()
