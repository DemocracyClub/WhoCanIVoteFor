from django.core.management.base import BaseCommand
from elections.models import PostElection
from elections.wikipedia_map import ballot_to_wikipedia
from people.helpers import get_wikipedia_extract
from people.models import Person, PersonPost
from requests.exceptions import RequestException


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--current",
            action="store_true",
            dest="current",
            default=False,
            help="Only import bios for current candidates",
        )

    def update_people(self, current):
        people = Person.objects.exclude(wikipedia_url=None)
        if current:
            current_candidacies = PersonPost.objects.current()
            people = (
                people.filter(personpost__in=current_candidacies)
                .order_by()
                .distinct()
            )

        for person in people:
            current_bio = person.wikipedia_bio
            try:
                new_bio = get_wikipedia_extract(person.wikipedia_url)
                if current_bio != new_bio:
                    person.wikipedia_bio = new_bio
                    person.save()
            except RequestException:
                pass

    def update_ballots(self, current):
        parl_ballots = PostElection.objects.filter(
            ballot_paper_id__startswith="parl."
        )
        if current:
            parl_ballots = parl_ballots.filter(election__current=True)

        for ballot in parl_ballots:
            start = ".".join(ballot.ballot_paper_id.split(".")[:-1]) + "."
            if start in ballot_to_wikipedia:
                ballot.wikipedia_url = ballot_to_wikipedia[start]
                current_bio = ballot.wikipedia_bio

                try:
                    new_bio = get_wikipedia_extract(ballot.wikipedia_url)
                    if current_bio != new_bio:
                        ballot.wikipedia_bio = new_bio
                        ballot.save()
                except RequestException:
                    pass

    def handle(self, **options):
        self.update_people(options["current"])
        self.update_ballots(options["current"])
