from datetime import datetime, timedelta
import json
import random

import requests

from django.core.management.base import BaseCommand
from django.conf import settings

from feedback.models import Feedback


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--hours-ago",
            action="store",
            dest="hours",
            default=1,
            type=int,
            help="Hours to look back for feedback",
        )

    @property
    def random_happy(self):
        return random.choice(
            [
                ":+1:",
                ":tada:",
                ":grinning:",
                ":heart_eyes:",
                ":heart_eyes_cat:",
                ":heart:",
                ":laughing:",
                ":sunny:",
                ":white_check_mark:",
                ":star:",
                ":smile:",
            ]
        )

    @property
    def random_sad(self):
        return random.choice(
            [
                ":-1:",
                ":disappointed:",
                ":confused:",
                ":unamused:",
                ":rage:",
                ":confounded:",
                ":hankey:",
                ":red_circle:",
                ":x:",
                ":cry:",
            ]
        )

    def format_attachment(self, comment):
        useful_colour = "#2AB27B"
        not_useful_colour = "#C7254E"

        colour = useful_colour
        comment_title = "A 'found' comment:"
        if comment.found_useful == "NO":
            comment_title = "A 'not found' comment:"
            colour = not_useful_colour
        useful_comment = {
            "fallback": comment.comments,
            "color": colour,
            "fields": [
                {
                    "title": comment_title,
                    "value": comment.comments,
                    "short": False,
                },
                {
                    "title": "Other sources",
                    "value": comment.sources,
                    "short": False,
                },
                {
                    "title": "Page",
                    "value": "<{0}{1}>".format(
                        settings.CANONICAL_URL, comment.source_url
                    ),
                    "short": False,
                },
            ],
        }
        return useful_comment

    def handle(self, **options):
        past_time = datetime.now() - timedelta(hours=int(options["hours"]))

        msg_fmt = """Feedback time!\nIn the last {hour_string}:\n\t{found} people felt {random_happy}\n\t{not_found} people felt {random_sad}\n"""

        recent_feedback = Feedback.objects.filter(created__gte=past_time)

        if not recent_feedback.exists():
            return

        found = recent_feedback.filter(found_useful="YES")
        not_found = recent_feedback.exclude(found_useful="YES")

        hour_string = "hour"
        if options["hours"] > 1:
            hour_string = "{} hours".format(options["hours"])

        message = msg_fmt.format(
            hour_string=hour_string,
            found=found.count(),
            not_found=not_found.count(),
            random_happy=self.random_happy,
            random_sad=self.random_sad,
        )

        payload = {"text": message}

        found_useful_comments = found.exclude(comments="")[:2]
        not_found_useful_comments = not_found.exclude(comments="")[:2]
        attachments = []

        for comment in found_useful_comments:
            attachments.append(self.format_attachment(comment))
        for comment in not_found_useful_comments:
            attachments.append(self.format_attachment(comment))

        if attachments:
            payload["attachments"] = attachments

        if getattr(settings, "SLACK_FEEDBACK_WEBHOOK_URL", None):
            url = settings.SLACK_FEEDBACK_WEBHOOK_URL
            requests.post(url, json.dumps(payload), timeout=2)
