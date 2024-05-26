"""
Importer for all our important Hustings data
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from elections.models import PostElection
from hustings.importers import HustingImporter
from hustings.models import Husting

from wcivf.utils import NoOpOutputWrapper


def dt_from_string(dt):
    """
    Given a date string DT, return a datetime object.
    """
    try:
        date = datetime.datetime.strptime(dt, "%d-%m-%Y")
    except ValueError:
        pass
    except TypeError:
        return None
    else:
        return timezone.make_aware(date, timezone.get_current_timezone())

    # kept for legacy reasons - previous years used different date formatting
    try:
        date = datetime.datetime.strptime(dt, "%Y-%b-%d")
    except ValueError:
        date = datetime.datetime.strptime(dt, "%Y-%B-%d")

    return timezone.make_aware(date, timezone.get_current_timezone())


def stringy_time_to_inty_time(stringy_time):
    """
    Given a string in the form HH:MM return integer values for hour
    and minute.
    """
    hour, minute = stringy_time.split(":")
    return int(hour), int(minute)


def set_time_string_on_datetime(dt, time_string):
    """
    Given a datetime DT and a string in the form HH:MM return a
    new datetime with the hour and minute set according to
    TIME_STRING
    """
    hour, minute = stringy_time_to_inty_time(time_string)
    return dt.replace(hour=hour, minute=minute)


class Command(BaseCommand):
    URLS = [
        # 2024 GE
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vRQ2M-Kwm8LVvT-eu89wP5bt-ffE0bClfdB0iegFSnoHep_k8bdYk1Ndl5XlwvzMKleynlDOXhYXET8/pub?gid=0&single=true&output=csv",
        # 2024 Locals
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vRQ2M-Kwm8LVvT-eu89wP5bt-ffE0bClfdB0iegFSnoHep_k8bdYk1Ndl5XlwvzMKleynlDOXhYXET8/pub?gid=0&single=true&output=csv",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--filename",
            required=False,
            help="Path to the file with the hustings in it",
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            dest="quiet",
            default=False,
            help="Only output errors",
        )
        parser.add_argument(
            "--urls",
            "-u",
            dest="urls",
            nargs="+",
            required=False,
            help="Specify a URLs to a google sheet to import from",
        )

    def create_husting(self, row):
        """
        Create an individual husting
        """
        # kept the second option to work with previous years spreadsheets
        starts = row.get("Date (DD-MM-YYYY)") or row.get("Date (YYYY-Month-DD)")
        starts = dt_from_string(starts)
        if not starts:
            return None

        ends = None
        if row["Start time (00:00)"]:
            starts = set_time_string_on_datetime(
                starts, row["Start time (00:00)"]
            )
        if row["End time (if known)"]:
            ends = set_time_string_on_datetime(
                starts, row["End time (if known)"]
            )

        # Get the post_election
        pes = PostElection.objects.filter(ballot_paper_id=row["Election ID"])
        if not pes.exists():
            # This might be a parent election ID
            pes = PostElection.objects.filter(election__slug=row["Election ID"])
        husting = None
        for pe in pes:
            husting = Husting.objects.create(
                post_election=pe,
                title=row["Title of event"],
                url=row["Link to event information"],
                starts=starts,
                ends=ends,
                location=row.get(
                    "Location (if online only please leave blank)", ""
                ),
                postevent_url=row[
                    "Link to post-event information (e.g. blog post, video)"
                ],
            )
        return husting

    def import_hustings(self):
        for row in self.importer.rows:
            try:
                husting = self.create_husting(row)
            except ValueError as e:
                self.stdout.write(repr(e))
                husting = None

            if not husting:
                title = row.get("Title of event", None)
                if title:
                    self.stdout.write(f"Couldn't create {title}")
                else:
                    self.stdout.write(f"Something went wrong with {row}")
                continue

            self.hustings_counter += 1
            self.stdout.write(
                "Created husting {0} <{1}>".format(
                    self.hustings_counter, husting.post_election.ballot_paper_id
                )
            )

    @transaction.atomic
    def handle(self, **options):
        """
        Entry point for our command.
        """
        if options["quiet"]:
            self.stdout = NoOpOutputWrapper()

        file = options["filename"]
        if file:
            answer = input(
                "All hustings will be deleted and replaced with only those included in the file proved. Do you want to continue? y/n\n"
            )
            if answer != "y":
                return None

        count, _ = Husting.objects.all().delete()
        self.stdout.write(f"Deleting {count} Husting objects")

        self.hustings_counter = 0
        if file:
            self.importer = HustingImporter(file_path=options["filename"])
            return self.import_hustings()

        urls = options["urls"] or self.URLS
        for url in urls:
            self.importer = HustingImporter(url=url)
            self.import_hustings()
        return None
