"""
Importer for all our important Hustings data
"""
import os
import csv
import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from elections.models import PostElection
from hustings.models import Husting


def dt_from_string(dt):
    """
    Given a date string DT, return a datetime object.
    Try multiple strptime formats b/c Google sheets doesn't
    understand counting to three.
    """
    date = None
    try:
        date = datetime.datetime.strptime(dt, "%Y-%b-%d")
    except ValueError:
        date = datetime.datetime.strptime(dt, "%Y-%B-%d")
    if date:
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
    dt = dt.replace(hour=hour, minute=minute)
    return dt


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "filename", help="Path to the file with the hustings in it"
        )
        parser.add_argument(
            "--quiet",
            action="store_true",
            dest="quiet",
            default=False,
            help="Only output errors",
        )
        parser.add_argument(
            "--for-date",
            action="store",
            dest="date",
            required=True,
            help="The date of the elections this file is about",
        )

    def delete_all_hustings(self, election_date):
        """
        Clear our hustings away.
        """
        Husting.objects.filter(
            post_election__election__election_date=election_date
        ).delete()

    def create_husting(self, row):
        """
        Create an individual husting
        """
        starts = dt_from_string(row["Date (YYYY-Month-DD)"])
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
        for pe in pes:
            husting = Husting(
                post_election=pe,
                title=row["Title of event"],
                url=row["Link to event information"],
                starts=starts,
                ends=ends,
                location=row["Name of event location (e.g. Church hall)"],
                postcode=row["Postcode of event location"],
                postevent_url=row[
                    "Link to post-event information (e.g. blog post, video)"
                ],
            )
            husting.save()

    @transaction.atomic
    def handle(self, **options):
        """
        Entry point for our command.
        """
        if options["quiet"]:
            self.stdout = open(os.devnull, "w")

        for_election = options["date"]

        self.delete_all_hustings(for_election)
        hustings_counter = 0
        self.not_a_constituency_friend = []
        with open(options["filename"], "r") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    husting = self.create_husting(row)
                except:
                    husting = None
                if husting:
                    hustings_counter += 1
                    self.stdout.write(
                        "Created husting {0} <{1}>".format(
                            hustings_counter, husting
                        )
                    )
