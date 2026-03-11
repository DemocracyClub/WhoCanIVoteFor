"""
Models for Hustings
"""

import hashlib

from django.contrib.sites.models import Site
from django.db import models
from django.db.models import TextChoices
from django.urls import reverse
from django.utils import timezone
from elections.models import PostElection
from model_utils.models import TimeStampedModel


class HustingQueryset(models.QuerySet):
    def future(self):
        """
        Returns QuerySet of objects in the future or today
        """
        return self.published().filter(starts__date__gte=timezone.now().date())

    def displayable(self):
        """
        Excludes objects in the past unless we have a postevent url for them
        """
        return self.published().exclude(
            starts__date__lt=timezone.now().date(),
            postevent_url="",
        )

    def published(self):
        return self.filter(status=HustingStatus.published)


class HustingStatus(TextChoices):
    suggested = "suggested", "Suggested"
    published = "published", "Published"
    rejected = "rejected", "Rejected"
    unpublished = "unpublished", "Unpublished"


class Husting(TimeStampedModel):
    """
    A Husting.
    """

    post_election = models.ForeignKey(PostElection, on_delete=models.CASCADE)
    title = models.CharField(
        max_length=250, help_text="The title or topic of the husting"
    )
    url = models.URLField(
        max_length=800,
        help_text="A webpage where people can find more information and/or sign up to attend",
        verbose_name="URL",
        blank=True,
    )
    starts = models.DateTimeField(
        help_text="The date and time the event starts"
    )
    ends = models.DateTimeField(blank=True, null=True)
    location = models.CharField(
        max_length=250,
        blank=True,
        default="",
        help_text="Descriptive text or address of the location (if online write 'internet')",
    )
    postevent_url = models.URLField(blank=True, max_length=800)
    status = models.CharField(
        default=HustingStatus.suggested, choices=HustingStatus.choices
    )

    objects = HustingQueryset.as_manager()

    class Meta:
        ordering = ["-starts"]

    @property
    def in_past(self):
        return self.starts.date() < timezone.now().date()

    @property
    def uuid(self):
        """
        Build a uuid to be used when creating an iCal event for the object
        """
        s = f"{self.title}{self.starts.timestamp()}"
        return hashlib.md5(s.encode("utf-8")).hexdigest()

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk],
        )

    def as_slack_blocks(self) -> list:
        """
        Return Slack Block payload blocks for a husting, for use in the
        Slack Helper
        """

        starts = self.starts
        starts_str = starts.strftime("%A %-d %B %Y at %-I:%M%p")

        url = self.url.strip() if self.url else ""
        location = self.location.strip() if self.location else ""
        ends = self.ends if self.ends else None

        current_site = Site.objects.get_current()
        admin_url = f"https://{current_site.domain}{self.get_admin_url()}"

        fields = [
            {
                "type": "mrkdwn",
                "text": f"*Ballot*\n{self.post_election}",
            },
            {
                "type": "mrkdwn",
                "text": f"*Starts*\n{starts_str}",
            },
        ]

        if ends:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*Ends*\n{ends.strftime('%A %-d %B %Y at %-I:%M%p')}",
                }
            )

        if location:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*Location*\n{location}",
                }
            )

        if url:
            fields.append(
                {
                    "type": "mrkdwn",
                    "text": f"*URL*\n<{url}|Open event page>",
                }
            )

        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "New husting added",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{self.title}*",
                },
            },
            {
                "type": "section",
                "fields": fields,
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Moderate in admin",
                            "emoji": True,
                        },
                        "url": admin_url,
                        "style": "primary",
                    }
                ],
            },
        ]
