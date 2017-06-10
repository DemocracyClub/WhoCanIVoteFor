from django.db import models

from elections.models import PostElection
from people.models import PersonPost


class ResultEvent(models.Model):
    post_election = models.OneToOneField(PostElection)
    person_posts = models.ManyToManyField(PersonPost)
    expected_declaration_time = models.DateTimeField(blank=True, null=True)
    declaration_time = models.DateTimeField(blank=True, null=True)
