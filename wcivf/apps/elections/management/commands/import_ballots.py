from django.core.management.base import BaseCommand
from elections.import_helpers import (
    EEHelper,
    YNRBallotImporter,
    time_function_length,
)
from elections.models import Election, PostElection


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--current",
            action="store_true",
            dest="current",
            default=False,
            help="Only import ballots that are'current'",
        )
        parser.add_argument(
            "--force-update",
            action="store_true",
            dest="force_update",
            default=False,
            help="Imports all properties from EE",
        )
        parser.add_argument(
            "--force-all-metadata",
            action="store_true",
            dest="force_metadata",
            default=False,
            help="Imports all metadata from EE for all elections",
        )
        parser.add_argument(
            "--recently-updated",
            action="store_true",
            dest="recently_updated",
            help="Only import ballots updated since the last known update",
        )
        parser.add_argument(
            "--exclude-candidacies",
            action="store_true",
            dest="exclude_candidacies",
            default=False,
            help="Ignore candidacies when importing ballots",
        )

    @time_function_length
    def populate_any_non_by_elections_field(self):
        """
        Finds all current non by-election ballots and makes sure that
        their parent Election objects have the any_non_by_elections
        field set
        """
        any_non_by_election_ballots = (
            PostElection.objects.filter(
                election__current=True,
            )
            .exclude(ballot_paper_id__contains=".by.")
            .distinct()
        )
        Election.objects.filter(
            postelection__in=any_non_by_election_ballots
        ).update(any_non_by_elections=True)

    @time_function_length
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
            force_update=options["force_update"],
            stdout=self.stdout,
            current_only=options["current"],
            force_metadata=options["force_metadata"],
            recently_updated=options["recently_updated"],
            exclude_candidacies=options["exclude_candidacies"],
        )
        importer.do_import()
        self.populate_any_non_by_elections_field()
        self.delete_deleted_elections()
