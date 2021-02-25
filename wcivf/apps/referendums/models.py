from django.db import models


class Referendum(models.Model):

    ballots = models.ManyToManyField(
        to="elections.PostElection",
        related_name="referendums",
    )
    question = models.CharField(max_length=255)
    council_name = models.CharField(max_length=255)
    answer_one = models.CharField(max_length=255, blank=True)
    answer_two = models.CharField(max_length=255, blank=True)
    council_url = models.URLField(max_length=255, blank=True)
    answer_one_campaign_url = models.URLField(max_length=255, blank=True)
    answer_two_campaign_url = models.URLField(max_length=255, blank=True)

    def __str__(self):
        return self.question
