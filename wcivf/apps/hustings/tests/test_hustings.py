from django.test import TestCase
from django.utils.timezone import datetime, utc
from freezegun import freeze_time

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

    @freeze_time("2017-3-22")
    @vcr.use_cassette("fixtures/vcr_cassettes/test_mayor_elections.yaml")
    def test_hustings_display_on_postcode_page(self):

        response = self.client.get("/elections/e32nx", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.hust.title)
        self.assertContains(response, self.hust.url)
        self.assertContains(response, self.hust.postcode)

    @freeze_time("2017-3-22")
    def test_hustings_display_on_ballot_page(self):
        response = self.client.get(self.ballot.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.hust.title)
        self.assertContains(response, self.hust.url)
        self.assertContains(response, self.hust.postcode)

    @freeze_time("2021-4-1")
    def test_displayable_in_past_not_returned(self):
        result = Husting.objects.displayable()
        assert self.hust not in result
        assert result.count() == 0

    @freeze_time("2021-4-1")
    def test_displayable_in_past_with_postevent_url_is_returned(self):
        self.hust.starts = datetime(2021, 3, 31, tzinfo=utc)
        self.hust.postevent_url = "http://example.com/"
        self.hust.save()
        result = Husting.objects.displayable()
        assert self.hust in result
        assert result.count() == 1

    @freeze_time("2021-4-1")
    def test_displayable_in_future_always_returned(self):
        self.hust.starts = datetime(2021, 4, 2, tzinfo=utc)
        self.hust.save()
        result = Husting.objects.displayable()
        assert self.hust in result
        assert result.count() == 1

    @freeze_time("2021-4-1")
    def test_displayable_on_day_always_returned(self):
        self.hust.starts = datetime(2021, 4, 1, tzinfo=utc)
        self.hust.save()
        result = Husting.objects.displayable()
        assert self.hust in result
        assert result.count() == 1

    @freeze_time("2021-4-1")
    def test_future(self):
        past = Husting.objects.get(pk=self.hust.pk)

        today = Husting.objects.get(pk=self.hust.pk)
        today.pk = None
        today.starts = datetime(2021, 4, 1, tzinfo=utc)
        today.save()

        future = Husting.objects.get(pk=self.hust.pk)
        future.pk = None
        future.starts = datetime(2021, 4, 2, tzinfo=utc)
        future.save()

        result = Husting.objects.future()
        assert past not in result
        assert today in result
        assert future in result
        assert result.count() == 2
