import os

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.core.management import call_command

from elections.constants import (
    PEOPLE_FOR_BALLOT_KEY_FMT,
    POSTCODE_TO_BALLOT_KEY_FMT,
    POLLING_STATIONS_KEY_FMT,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            dest="full",
            default=False,
            help="Import all data, not just people",
        )

    def handle(self, **options):

        if options["full"]:
            commands = [
                ("import_parties",),
                ("import_ballots",),
                ("import_people",),
            ]
        else:
            commands = [("import_people", "--recent")]

        for command in commands:
            print(" ".join(command))
            call_command(*command)

        if options["full"]:
            # Delete the cache on a full import
            if hasattr(cache, "delete_pattern"):
                for fmt in (
                    POLLING_STATIONS_KEY_FMT,
                    POSTCODE_TO_BALLOT_KEY_FMT,
                    PEOPLE_FOR_BALLOT_KEY_FMT,
                ):
                    cache.delete_pattern(fmt.format("*"))

        # Unset dirty file if it exists
        if getattr(settings, "CHECK_HOST_DIRTY", False):
            dirty_file_path = os.path.expanduser(
                getattr(settings, "DIRTY_FILE_PATH")
            )

            if os.path.exists(dirty_file_path):
                os.remove(dirty_file_path)
