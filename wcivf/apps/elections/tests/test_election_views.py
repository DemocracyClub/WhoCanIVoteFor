import pytest
from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import override_settings
from elections.models import Post
from elections.tests.factories import (
    ElectionFactory,
    ElectionFactoryLazySlug,
    ElectionWithPostFactory,
    PostElectionFactory,
    PostFactory,
)
from people.tests.factories import PersonFactory, PersonPostFactory
from pytest_django.asserts import assertContains, assertNotContains


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class ElectionViewTests(TestCase):
    def setUp(self):
        self.election = ElectionWithPostFactory(
            name="City of London Corporation local election",
            election_date="2017-03-23",
            slug="local.city-of-london.2017-03-23",
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

    def test_division_name_displayed(self):
        """
        For each Post.DIVISION_TYPE, creates an elections, gets a response for
        from the ElectionDetail view, and checks that the response contains the
        correct value for division name .e.g Ward
        """
        Post.DIVISION_TYPE_CHOICES.append(("", ""))
        for division_type in Post.DIVISION_TYPE_CHOICES:
            election = ElectionWithPostFactory(
                ballot__post__division_type=division_type[0]
            )
            with self.subTest(election=election):
                response = self.client.get(
                    election.get_absolute_url(), follow=True
                )
                self.assertContains(
                    response, election.pluralized_division_name.title()
                )


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


@pytest.mark.django_db
class TestPostViewName:
    @pytest.fixture(params=Post.DIVISION_TYPE_CHOICES)
    def post_obj(self, request):
        """
        Fixture to create a Post object with each division choice
        """
        return PostFactory(division_type=request.param[0])

    def test_name_correct(self, post_obj, client):
        """
        Test that the correct names for the post and post election objects are
        displayed
        """
        post_election = PostElectionFactory(post=post_obj)

        response = client.get(
            post_election.get_absolute_url(),
            follow=True,
        )
        assertContains(response, post_election.friendly_name)
        assertContains(response, post_election.post.full_label)

    def test_by_election(self, client):
        """
        Test for by elections
        """
        post_election = PostElectionFactory(
            ballot_paper_id="local.by.election.2020"
        )

        response = client.get(post_election.get_absolute_url(), follow=True)
        assertContains(response, "by-election")
        assertContains(response, post_election.friendly_name)
        assertContains(response, post_election.post.label)


class TestPostViewNextElection:
    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_election_displayed(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        # create a future election expected to be displayed
        PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )

        response = client.get(past.get_absolute_url(), follow=True)
        assertContains(response, "<h3>Next election</h3>")
        assertContains(
            response,
            "due to take place <strong>on Thursday 6 May 2021</strong>.",
        )

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_election_not_displayed(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        response = client.get(past.get_absolute_url(), follow=True)
        assertNotContains(response, "<h3>Next election</h3>")

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-7")
    def test_next_election_not_displayed_in_past(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        # create an election that just passed
        PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )
        response = client.get(past.get_absolute_url(), follow=True)
        assertNotContains(response, "<h3>Next election</h3>")

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_election_not_displayed_for_current_election(self, client):
        post = PostFactory()
        current = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )
        response = client.get(current.get_absolute_url(), follow=True)
        assertNotContains(response, "<h3>Next election</h3>")

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-6")
    def test_next_election_is_today(self, client):
        post = PostFactory()
        past = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-2",
                current=False,
            ),
        )
        # create an election taking place today
        PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
            ),
        )
        response = client.get(past.get_absolute_url(), follow=True)
        assertContains(response, "<h3>Next election</h3>")
        assertContains(response, "<strong>being held today</strong>.")
