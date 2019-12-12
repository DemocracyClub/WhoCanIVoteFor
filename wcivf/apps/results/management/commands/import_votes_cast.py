from django.core.management.base import BaseCommand
from django.conf import settings

from core.helpers import show_data_on_error
from elections.helpers import JsonPaginator
from people.models import PersonPost
from results.models import PersonPostResult
from elections.models import PostElection


class Command(BaseCommand):
    help = "Import results from the YNR API"

    # def add_arguments(self, parser):
    # Add back in again when we have date filters in YNR
    # parser.add_argument(
    #     "--date", action="store", dest="date", help="The election date"
    # )

    def handle(self, *args, **options):
        base_url = "{}/api/next/results/?page_size=200".format(
            settings.YNR_BASE
        )
        next_page = base_url
        for page in JsonPaginator(next_page, self.stdout):
            self.import_page(page["results"])

    def import_page(self, results):
        for resultset in results:
            post_election = PostElection.objects.get(
                ballot_paper_id=resultset["ballot"]["ballot_paper_id"]
            )
            for candidacy in resultset["candidate_results"]:
                with show_data_on_error("Membership", candidacy):
                    try:
                        person_post = PersonPost.objects.get(
                            post_election=post_election,
                            person__ynr_id=candidacy["person"]["id"],
                        )
                    except PersonPost.DoesNotExist:
                        continue
                    person_post.elected = candidacy["elected"]
                    person_post.save()

                    PersonPostResult.objects.update_or_create(
                        person_post=person_post,
                        defaults={"votes_cast": candidacy["num_ballots"]},
                    )
