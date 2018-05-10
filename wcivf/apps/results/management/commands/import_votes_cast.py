import requests

from django.core.management.base import BaseCommand
from django.conf import settings

from people.models import PersonPost
from results.models import PersonPostResult
from elections.models import PostElection


class Command(BaseCommand):
    help = "Import results from the YNR API"

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            action='store',
            dest='date',
            required=True,
            help='The election date',
        )

    def handle(self, *args, **options):
        base_url = "{}/api/v0.9/result_sets/?election_date={}".format(
            settings.YNR_BASE,
            options['date']
        )
        next_page = base_url
        while next_page:
            req = requests.get(next_page)
            data = req.json()
            self.import_page(data['results'])
            next_page = data.get('next')

    def import_page(self, results):
        for resultset in results:
            post_election = PostElection.objects.get(
                ballot_paper_id=resultset['ballot_paper_id']
            )
            for membership in resultset['candidate_results']:
                person_post = PersonPost.objects.get(
                    post_election=post_election,
                    person__pk=membership['membership']['person']['id']
                )
                person_post.elected = membership['is_winner']
                person_post.save()

                PersonPostResult.objects.update_or_create(
                    person_post=person_post,
                    votes_cast=membership['num_ballots']
                )
