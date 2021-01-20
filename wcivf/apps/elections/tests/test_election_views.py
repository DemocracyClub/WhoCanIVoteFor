import pytest
from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import override_settings
from elections.models import PostElection
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
    PostFactory,
)
from people.tests.factories import PersonFactory, PersonPostFactory


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class ElectionViewTests(TestCase):
    def setUp(self):
        self.election = ElectionFactory(
            name="City of London Corporation local election",
            election_date="2017-03-23",
            slug="local.city-of-london.2017-03-23",
        )
        self.post = PostFactory(
            ynr_id="LBW:E05009288", label="Aldersgate", elections=self.election
        )
        PostElection.objects.get_or_create(
            election=self.election,
            post=self.post,
            ballot_paper_id="local.city-of-london.aldersgate.2017-03-23",
        )

    def test_election_list_view(self):
        with self.assertNumQueries(2):
            url = reverse("elections_view")
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "elections/elections_view.html")
            self.assertContains(response, self.election.nice_election_name)

    def test_election_detail_view(self):
        response = self.client.get(
            self.election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/election_view.html")
        self.assertContains(response, self.election.nice_election_name)

    @pytest.mark.freeze_time("2017-03-23")
    def test_election_detail_day_of_election(self):
        """
        Test the wording of poll open/close times for both an election within
        City of London, and for another election not in City of London
        """
        not_city_of_london = ElectionFactory(
            slug="not.city-of-london",
            election_date="2017-03-23",
        )
        PostElectionFactory(election=not_city_of_london)

        for election in [
            (self.election, "Polls are open from 8a.m. till 8p.m."),
            (not_city_of_london, "Polls are open from 7a.m. till 10p.m."),
        ]:
            with self.subTest(election=election):
                response = self.client.get(
                    election[0].get_absolute_url(), follow=True
                )
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response, "elections/election_view.html"
                )
                self.assertContains(response, election[0].nice_election_name)
                self.assertContains(response, election[1])


class ElectionPostViewTests(TestCase):
    def setUp(self):
        self.election = ElectionFactory(
            name="Adur local election",
            election_date="2021-05-06",
            slug="local.adur.churchill.2021-05-06",
        )
        self.post = PostFactory(label="Adur local election")
        self.post_election = PostElectionFactory(
            election=self.election, post=self.post
        )

    def test_zero_candidates(self):
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/post_view.html")
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_title.html"
        )
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_description.html"
        )
        self.assertContains(response, "No candidates known yet.")

    def test_num_candidates(self):
        people = [PersonFactory() for p in range(5)]
        for person in people:
            PersonPostFactory(
                post_election=self.post_election,
                election=self.election,
                post=self.post,
                person=person,
            )

        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/post_view.html")
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_title.html"
        )
        self.assertTemplateUsed(
            response, "elections/includes/_post_meta_description.html"
        )
        self.assertContains(response, f"The 5 candidates in {self.post.label}")
        self.assertContains(
            response, f"See all 5 candidates in the {self.post.label}"
        )
