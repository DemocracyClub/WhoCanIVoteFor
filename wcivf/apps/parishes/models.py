from django.db import models
from django.utils import timezone


class ParishCouncilElection(models.Model):
    council_name = models.CharField(max_length=255)
    parish_ward_name = models.CharField(max_length=255, blank=True)
    ballots = models.ManyToManyField(
        to="elections.PostElection",
        related_name="parish_councils",
    )
    local_authority = models.CharField(max_length=255)
    council_type = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    precept = models.CharField(
        max_length=255,
        blank=True,
        help_text="The amount of the parish councils share of the council tax",
    )
    sopn = models.URLField(blank=True, help_text="Link to SoPN PDF")
    ward_seats = models.PositiveIntegerField(default=0)
    is_contested = models.NullBooleanField(default=None)

    @property
    def in_past(self):
        """
        Check if the election is in the past
        """
        return timezone.now().date() > self.election_date

    @property
    def is_uncontested(self):
        """
        Check if is_contested is explicity False rather than None
        """
        return self.is_contested is False

    @property
    def election_date(self):
        """
        Hardcoded for this round of elections. This is used to correctly group
        the election with other elections when displayed in
        inline_elections_nav_list.html
        """
        return timezone.datetime(2021, 5, 6).date()
