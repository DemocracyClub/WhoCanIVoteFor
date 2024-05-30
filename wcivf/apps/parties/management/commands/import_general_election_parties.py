from dateutil.parser import parse
from django.core.management.base import BaseCommand
from django.db import transaction
from parties.importers import (
    GeneralElection,
    GeneralElectionPartyImporter,
)
from parties.models import GeneralElectionParty


class Command(BaseCommand):
    ELECTIONS = [
        GeneralElection(
            date="2024-07-04",
            csv_files=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vS0GJ6wED4d87K1AMXTxxfYl1L-RwjuH-DY1lcwAH9Wj8MChrxPRVDXqc1dzMW8sVdGDLXcBi0usnDl/pub?gid=0&single=true&output=csv"
            ],
        )
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

        election = GeneralElectionParty(date=date, csv_files=[filepath])
        importer = GeneralElectionPartyImporter(
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
            importer = GeneralElectionPartyImporter(
                election=election,
                force_update=self.options["force_update"],
            )
            importer.import_parties()

    def import_from_url(self):
        """
        Runs the importer for all elections in the ELECTIONS list. This is the
        default method of running the import process
        """
        election = GeneralElectionParty(
            date=self.options["date"], csv_files=[self.options["url"]]
        )
        importer = GeneralElectionPartyImporter(
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
