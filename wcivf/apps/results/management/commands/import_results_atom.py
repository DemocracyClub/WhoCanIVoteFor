import feedparser
import requests

from django.core.management.base import BaseCommand
from django.conf import settings

from core.helpers import show_data_on_error
from people.models import PersonPost
from elections.models import PostElection
from results.models import ResultEvent


class Command(BaseCommand):
    help = "Import results from the YNR Atom feed"

    def handle(self, *args, **options):
        feed_url = "{}/results/all.atom".format(settings.YNR_BASE)
        req = requests.get(feed_url)
        feed = feedparser.parse(req.text)
        for entry in feed["entries"]:
            with show_data_on_error("Result", entry):
                post_election = PostElection.objects.get(
                    election__slug=entry["election_slug"],
                    post__ynr_id=entry["post_id"],
                )
                person_post = PersonPost.objects.get(
                    person_id=entry["winner_person_id"],
                    post_election=post_election,
                )

                result_event, _ = ResultEvent.objects.update_or_create(
                    post_election=post_election,
                    defaults={"declaration_time": entry["published"]},
                )

                if int(entry["retraction"]) == 1:
                    # The result has been retracted due to an error
                    # Unset the elected flag
                    person_post.elected = None
                    result_event.person_posts.remove(person_post)
                else:
                    person_post.elected = True
                    result_event.person_posts.add(person_post)
                person_post.save()
                result_event.save()
