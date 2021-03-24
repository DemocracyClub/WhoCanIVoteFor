from django.db import models


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
    def is_contested_known(self):
        return self.is_contested is not None
