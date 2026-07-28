import csv
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from feedback.models import Feedback


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--since-date",
            action="store",
            dest="since_date",
            type=str,
            help="Feedback since the given date",
        )

    def handle(self, **options):
        since_date = options.get("since_date")

        feedback_to_export = Feedback.objects.exclude(
            flagged_as_spam=True
        ).order_by("created")

        if since_date:
            date = datetime.strptime(since_date, "%Y-%m-%d")
            date = timezone.make_aware(date, timezone.get_current_timezone())
            feedback_to_export = feedback_to_export.filter(created__gte=date)

        fieldnames = [
            "created",
            "found_useful",
            "sources",
            "vote",
            "comments",
            "source_url",
        ]
        out = csv.DictWriter(self.stdout, fieldnames=fieldnames)
        out.writeheader()
        for feedback in feedback_to_export:
            out.writerow(
                {
                    "created": feedback.created,
                    "found_useful": feedback.found_useful,
                    "sources": feedback.sources,
                    "vote": feedback.vote,
                    "comments": feedback.comments,
                    "source_url": feedback.source_url,
                }
            )
