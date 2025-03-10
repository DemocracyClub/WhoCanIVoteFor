from dateutil.parser import parse
from django.core.management.base import BaseCommand
from django.db import transaction
from parties.importers import LocalElection, LocalPartyImporter


class Command(BaseCommand):
    ELECTIONS = [
        LocalElection(
            date="2025-05-01",
            csv_files=[
                # LibDem
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTd6sLnXiOSBEMv357NQprn5XUaWfAMvsdRlQyY10ZWkCVZl-FAQmdcxQxGgYjURbBf8g1L3501pJKy/pub?gid=0&single=true&output=csv",
                # Con
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTd6sLnXiOSBEMv357NQprn5XUaWfAMvsdRlQyY10ZWkCVZl-FAQmdcxQxGgYjURbBf8g1L3501pJKy/pub?gid=84663404&single=true&output=csv",
                # Lab
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTd6sLnXiOSBEMv357NQprn5XUaWfAMvsdRlQyY10ZWkCVZl-FAQmdcxQxGgYjURbBf8g1L3501pJKy/pub?gid=1874493069&single=true&output=csv",
                # Green
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTd6sLnXiOSBEMv357NQprn5XUaWfAMvsdRlQyY10ZWkCVZl-FAQmdcxQxGgYjURbBf8g1L3501pJKy/pub?gid=818921609&single=true&output=csv",
                # Reform
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTd6sLnXiOSBEMv357NQprn5XUaWfAMvsdRlQyY10ZWkCVZl-FAQmdcxQxGgYjURbBf8g1L3501pJKy/pub?gid=1157694678&single=true&output=csv",
                # Other
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vTd6sLnXiOSBEMv357NQprn5XUaWfAMvsdRlQyY10ZWkCVZl-FAQmdcxQxGgYjURbBf8g1L3501pJKy/pub?gid=836467868&single=true&output=csv",
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
        parser.add_argument(
            "--date",
            action="store",
            help="date",
            required=False,
        )
        parser.add_argument(
            "--url",
            action="store",
            help="url",
            required=False,
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

    def import_from_url(self):
        """
        Runs the importer for all elections in the ELECTIONS list. This is the
        default method of running the import process
        """
        election = LocalElection(
            date=self.options["date"], csv_files=[self.options["url"]]
        )
        importer = LocalPartyImporter(
            election=election,
        )
        importer.import_parties()

    @transaction.atomic
    def handle(self, **options):
        self.options = options

        if options["from_file"]:
            return self.import_from_file()

        if options["url"] and options["date"]:
            return self.import_from_url()

        self.import_from_elections()
        return None
