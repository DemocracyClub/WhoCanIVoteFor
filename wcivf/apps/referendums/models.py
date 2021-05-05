from django.db import models
from django.utils.text import slugify
from django.utils import timezone


class Referendum(models.Model):

    ballots = models.ManyToManyField(
        to="elections.PostElection",
        related_name="referendums",
    )
    question = models.CharField(max_length=255)
    council_name = models.CharField(max_length=255)
    area_name = models.CharField(max_length=255)
    date = models.DateField()
    answer_one = models.CharField(max_length=255, blank=True)
    answer_two = models.CharField(max_length=255, blank=True)
    council_url = models.URLField(max_length=255, blank=True)
    answer_one_campaign_url = models.URLField(max_length=255, blank=True)
    answer_two_campaign_url = models.URLField(max_length=255, blank=True)

    def __str__(self):
        return self.question

    @property
    def campaign_urls(self):
        """
        Return a list of all campaign urls, with null entrys removed
        """
        return list(
            filter(
                None,
                [self.answer_one_campaign_url, self.answer_two_campaign_url],
            )
        )

    @property
    def slug(self):
        return slugify(self.question)

    @property
    def is_election_day(self):
        """
        Return boolean for whether it is election day
        """
        return self.date == timezone.now().date()
