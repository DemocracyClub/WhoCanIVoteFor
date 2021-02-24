from dateutil.parser import parse

from django.core.management.base import BaseCommand
from django.db import transaction

from parties.importers import LocalPartyImporter, LocalElection


class Command(BaseCommand):
    ELECTIONS = [
        LocalElection(
            date="2018-05-03",
            csv_files=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vS3pC0vtT9WaCyKDzqARQZY6aoYCyKZLyIvumKaX3TpqG0rt4y0fXp6dOPOZGMX6v0dFczHfizwidwZ/pub?gid=582783400&single=true&output=csv",
            ],
        ),
        LocalElection(
            date="2019-05-02",
            csv_files=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTO-z37bBMxKwCuORIl2vE8v0kMFHlHETvBhGjuDidM1Wy4QxQawRou53kNLjEiJmpMhebRqoWZL9s-/pub?gid=0&single=true&output=csv",
            ],
        ),
        LocalElection(
            date="2021-05-06",
            csv_files=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1210343217&single=true&output=csv",
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=2091491905&single=true&output=csv",
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1013163356&single=true&output=csv",
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1273833263&single=true&output=csv",
            ],
        ),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "-f",
            "--force-update",
            action="store_true",
            help="Will update regardless of whether there are current elections for the date",
        )
        parser.add_argument(
            "-ff",
            "--from-file",
            nargs=2,
            metavar=("election_date", "path_to_file"),
            help="To import from a file, pass in an election date and the path to the file",
        )

    def valid_date(self, value):
        return parse(value)

    def import_from_file(self):
        """
        Runs the importer for the file passed in arguments
        """
        date, filepath = self.options["from_file"]
        if not self.valid_date(value=date):
            self.stdout.write("Date is invalid")
            return

        election = LocalElection(date=date, csv_files=[filepath])
        importer = LocalPartyImporter(
            election=election,
            force_update=self.options["force_update"],
            from_file=True,
        )
        importer.import_parties()

    def import_from_elections(self):
        """
        Runs the importer for all elections in the ELECTIONS list. This is the
        default method of running the import process
        """
        for election in self.ELECTIONS:
            importer = LocalPartyImporter(
                election=election,
                force_update=self.options["force_update"],
            )
            importer.import_parties()

    @transaction.atomic
    def handle(self, **options):
        self.options = options

        if options["from_file"]:
            return self.import_from_file()

        self.import_from_elections()
