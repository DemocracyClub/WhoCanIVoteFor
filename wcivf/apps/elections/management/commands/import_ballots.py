from django.core.management.base import BaseCommand

from elections.import_helpers import YNRBallotImporter, EEHelper
from elections.models import Election


class Command(YNRBallotImporter, BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--current",
            action="store_true",
            dest="current",
            default=False,
            help="Only import ballots that are'current'",
        )
        parser.add_argument(
            "--force-all-metadata",
            action="store_true",
            dest="force_metadata",
            default=False,
            help="Imports all metadata from EE for all elections",
        )
        parser.add_argument(
            "--force-current-metadata",
            action="store_true",
            dest="force_current_metadata",
            default=False,
            help="Imports all metadata from EE for current elections",
        )

    def populate_any_non_by_elections_field(self):
        qs = Election.objects.all().prefetch_related("postelection_set")
        for election in qs:
            any_non_by_elections = any(
                b.ballot_paper_id
                for b in election.postelection_set.all()
                if ".by." not in b.ballot_paper_id
            )
            election.any_non_by_elections = any_non_by_elections
            election.save()

    def delete_deleted_elections(self):
        """
        Deletes elections that are marked as deleted in Every Election and any
        related objects
        """
        ee_helper = EEHelper()
        elections, post_elections = ee_helper.delete_deleted_elections()
        self.stdout.write(
            f"Deleted {elections} Election objects and relations\n"
        )
        self.stdout.write(
            f"Deleted {post_elections} PostElection objects and relations\n"
        )

    def handle(self, **options):
        importer = YNRBallotImporter(
            stdout=self.stdout,
            current_only=options["current"],
            force_metadata=options["force_metadata"],
            force_current_metadata=options["force_current_metadata"],
        )
        importer.do_import()
        self.populate_any_non_by_elections_field()
        self.delete_deleted_elections()
