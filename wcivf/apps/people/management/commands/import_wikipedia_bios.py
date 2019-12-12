from django.core.management.base import BaseCommand

from elections.models import PostElection
from elections.wikipedia_map import ballot_to_wikipedia
from people.models import Person
from people.helpers import get_wikipedia_extract


class Command(BaseCommand):
    def handle(self, **options):
        for person in Person.objects.exclude(wikipedia_url=None).exclude(
            wikipedia_url=""
        ):
            person.wikipedia_bio = get_wikipedia_extract(person.wikipedia_url)
            person.save()

        qs = PostElection.objects.filter(ballot_paper_id__startswith="parl.")
        for ballot in qs:
            start = ".".join(ballot.ballot_paper_id.split(".")[:-1]) + "."
            if start in ballot_to_wikipedia:
                ballot.wikipedia_url = ballot_to_wikipedia[start]
                ballot.wikipedia_bio = get_wikipedia_extract(
                    ballot.wikipedia_url
                )
                ballot.save()
