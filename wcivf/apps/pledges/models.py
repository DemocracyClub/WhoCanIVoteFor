from django.db import models


class CandidatePledge(models.Model):
    person = models.ForeignKey(
        "people.person", related_name="pledges", on_delete=models.CASCADE
    )
    ballot_paper = models.ForeignKey(
        "elections.PostElection", on_delete=models.CASCADE
    )
    question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
