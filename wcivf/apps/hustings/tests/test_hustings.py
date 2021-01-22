from django.test import TestCase
from django.utils.timezone import datetime, utc

import vcr

from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
)
from hustings.models import Husting


class TestHustings(TestCase):
    def setUp(self):
        self.election = ElectionFactory(slug="mayor.tower-hamlets.2018-05-03")
        self.post = PostFactory(
            ynr_id="tower-hamlets",
            label="Tower Hamlets",
            elections=self.election,
        )
        self.ballot = PostElectionFactory(
            post=self.post,
            election=self.election,
            ballot_paper_id="mayor.tower-hamlets.2018-05-03",
        )

        self.hust = Husting.objects.create(
            post_election=self.ballot,
            title="Local Election Hustings",
            url="https://example.com/hustings",
            starts=datetime(2017, 3, 23, 19, 00, tzinfo=utc),
            ends=datetime(2017, 3, 23, 21, 00, tzinfo=utc),
            location="St George's Church",
            postcode="BN2 1DW",
        )

    @vcr.use_cassette("fixtures/vcr_cassettes/test_mayor_elections.yaml")
    def test_hustings_display_on_postcode_page(self):

        response = self.client.get("/elections/e32nx", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.hust.title)
        self.assertContains(response, self.hust.url)
        self.assertContains(response, self.hust.postcode)

    def test_hustings_display_on_ballot_page(self):
        response = self.client.get(self.ballot.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.hust.title)
        self.assertContains(response, self.hust.url)
        self.assertContains(response, self.hust.postcode)
