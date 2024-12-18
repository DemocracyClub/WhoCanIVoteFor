import datetime
from random import shuffle

import factory
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
from elections.views import PostView
from elections.views.mixins import PostelectionsToPeopleMixin
from parties.tests.factories import PartyFactory
from people.tests.factories import (
    PersonFactory,
    PersonPostFactory,
    PersonPostWithPartyFactory,
)
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
        with self.assertNumQueries(1):
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

    def test_election_type_filters(self):
        """
        Test that the election type filters
        return the correct query and url
        """
        local_election = ElectionWithPostFactory(
            slug="local.southfields.2022-06-23",
            election_date="2022-06-23",
            name="Southfields local election",
            election_type="local",
        )
        parl_election = ElectionWithPostFactory(
            slug="parl.2022-06-03/uk-parliament-elections/",
            election_date="2022-06-03",
            name="Parl 2022",
            election_type="parl",
        )
        url = reverse("elections_view")
        url = f"{url}?election_type={local_election.election_type}"
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "elections/elections_view.html")
        self.assertContains(response, local_election.nice_election_name)
        self.assertContains(response, local_election.get_absolute_url())
        self.assertContains(response, local_election.election_date)
        self.assertNotContains(response, parl_election.nice_election_name)

    def test_election_filters_exact_election_type(self):
        """
        Regresson test: previously we would get false positive results when
        filtering on 'parl', as 'europarl' also contains 'parl'. The lookup expression
        should be exact not "contains"
        """

        ElectionWithPostFactory(
            slug="europarl.uk-eastern.2014-05-22",
            election_date="2014-05-22",
            name="European Union Parliament (UK) elections: Eastern",
            election_type="europarl",
        )
        ElectionWithPostFactory(
            slug="parl.stroud.2019-12-12",
            election_date="2019-12-12",
            name="Stroud 2019",
            election_type="parl",
        )
        url = reverse("elections_view")
        url = f"{url}?election_type=parl"
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        print(response.content)
        self.assertNotContains(
            response, "European Union Parliament (UK) elections: Eastern"
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

    @pytest.mark.freeze_time("2024-04-10")
    def test_pre_sopn_text_with_candidates(self):
        future_election = ElectionFactory(
            name="Adur local election",
            election_date="2024-05-06",
            slug="local.adur.churchill.2024-05-06",
        )
        future_post = PostFactory(label="Adur local election")
        future_post_election = PostElectionFactory(
            election=future_election,
            post=future_post,
            ballot_paper_id="local.adur.churchill.2024-05-06",
        )
        future_post.territory = "ENG"
        future_post.save()
        person = PersonFactory()
        PersonPostFactory(
            post_election=future_post_election,
            election=future_election,
            post=future_post,
            person=person,
        )
        response = self.client.get(
            future_post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(future_post_election.locked)
        self.assertEqual(len(future_post_election.personpost_set.all()), 1)
        self.assertEqual(
            future_post_election.expected_sopn_date, datetime.date(2024, 4, 10)
        )
        pre_sopn_text_1 = (
            """We are currently aware of one candidate for this position."""
        )
        pre_sopn_text_2 = """The official candidate list will be published after 10 April 2024, when this page will be updated."""
        self.assertContains(response, pre_sopn_text_1)
        self.assertContains(response, pre_sopn_text_2)

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

    def test_cancellation_reason_candidate_death(self):
        self.post_election.cancelled = True
        self.post_election.cancellation_reason = "CANDIDATE_DEATH"
        self.post_election.save()
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
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            "This election was cancelled due to the death of a candidate.",
        )

    def test_cancellation_reason_no_candidates(self):
        self.post_election.cancelled = True
        self.post_election.cancellation_reason = "NO_CANDIDATES"
        self.post_election.save()
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
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            "This election was cancelled because no candidates stood for the available seats",
        )

    def test_cancellation_reason_equal_candidates(self):
        self.post_election.cancelled = True
        self.post_election.cancellation_reason = "EQUAL_CANDIDATES"
        self.post_election.save()
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
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            "This election was cancelled because the number of candidates who stood was equal to the number of available seats.",
        )

    def test_cancellation_reason_under_contested(self):
        self.post_election.cancelled = True
        self.post_election.cancellation_reason = "UNDER_CONTESTED"
        self.post_election.save()
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
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            "This election was cancelled because the number of candidates who stood was fewer than the number of available seats.",
        )

    def test_cancelled_with_metadata(self):
        """Case 1: Cancelled election and Metadata
        is set in EE"""
        self.post_election.winner_count = 4
        people = [PersonFactory() for p in range(4)]
        for person in people:
            PersonPostFactory(
                post_election=self.post_election,
                election=self.election,
                post=self.post,
                person=person,
            )
        self.post_election.cancelled = True
        self.post_election.save()
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
        self.assertTemplateUsed(
            response, "elections/includes/_cancelled_election.html"
        )
        self.assertNotContains(response, "No candidates known yet.")
        self.assertContains(
            response,
            f"{self.post_election.election.name}: This election has been cancelled",
        )

    def test_previous_cancelled_elections(self):
        """
        Previous elections table with cancelled election with unopposed candidate
        """
        self.person = PersonFactory()
        self.person_post = PersonPostFactory(
            post_election=self.post_election,
            election=self.election,
            post=self.post,
            person=self.person,
            elected=False,
        )
        self.post_election.cancelled = True
        self.post_election.save()
        response = self.client.get(self.person.get_absolute_url(), follow=True)
        self.assertContains(response, "{}'s elections".format(self.person.name))
        self.assertContains(response, "(election cancelled")

    def test_previous_elections_elected_with_count(self):
        """Previous elections table with elected candidate and vote count"""
        self.person = PersonFactory()
        self.person_post = PersonPostFactory(
            post_election=self.post_election,
            election=self.election,
            post=self.post,
            person=self.person,
            elected=True,
            votes_cast=10,
        )
        self.post_election.cancelled = False
        self.post_election.save()
        response = self.client.get(self.person.get_absolute_url(), follow=True)
        self.assertContains(response, "{}'s elections".format(self.person.name))
        self.assertContains(
            response, "{} votes (elected)".format(self.person_post.votes_cast)
        )

    def test_previous_elections_not_elected_with_count(self):
        self.person = PersonFactory()
        self.person_post = PersonPostFactory(
            post_election=self.post_election,
            election=self.election,
            post=self.post,
            person=self.person,
            elected=False,
            votes_cast=10,
        )
        self.post_election.cancelled = False
        self.post_election.save()
        response = self.client.get(self.person.get_absolute_url(), follow=True)
        self.assertContains(
            response,
            "{} votes (not elected)".format(self.person_post.votes_cast),
        )

    def test_previous_elections_elected_no_count(self):
        """Previous elections table with elected candidate and no vote count"""
        self.person = PersonFactory()
        self.person_post = PersonPostFactory(
            post_election=self.post_election,
            election=self.election,
            post=self.post,
            person=self.person,
            elected=True,
            votes_cast=None,
        )
        self.post_election.cancelled = False
        self.post_election.save()
        response = self.client.get(self.person.get_absolute_url(), follow=True)
        self.assertContains(response, "{}'s elections".format(self.person.name))
        self.assertContains(response, "Elected (vote count not available")

    def test_previous_elections_not_elected_no_count(self):
        """Previous elections table with no wins and no vote count"""
        self.person = PersonFactory()
        self.person_post = PersonPostFactory(
            post_election=self.post_election,
            election=self.election,
            post=self.post,
            person=self.person,
            elected=False,
            votes_cast=None,
        )
        self.post_election.cancelled = False
        self.post_election.save()
        response = self.client.get(self.person.get_absolute_url(), follow=True)
        self.assertContains(response, "{}'s elections".format(self.person.name))
        self.assertContains(response, "Not elected (vote count not available)")

    def test_deselected_person(self):
        self.person = PersonFactory()
        self.person_post = PersonPostFactory(
            post_election=self.post_election,
            election=self.election,
            post=self.post,
            person=self.person,
            elected=False,
            votes_cast=None,
            deselected=True,
            deselected_source="www.google.com",
        )
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertContains(
            response,
            "This candidate has been deselected by their party",
        )
        self.assertContains(response, "Learn more")


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
            ballot_paper_id="local.by.election.2020",
            election__any_non_by_elections=False,
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
            "due to take place on <strong>Thursday 6 May 2021</strong>.",
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


class TestPostViewTemplateName:
    @pytest.fixture
    def view_obj(self, rf):
        request = rf.get("/elections/ref.foo.2021-09-01/bar/")
        view = PostView()
        view.setup(request=request)
        return view

    @pytest.mark.parametrize(
        "boolean,template",
        [
            (True, "referendums/detail.html"),
            (False, "elections/post_view.html"),
        ],
    )
    def test_get_template_names(self, boolean, template, view_obj, mocker):
        view_obj.object = mocker.Mock(is_referendum=boolean)
        assert view_obj.get_template_names() == [template]


class TestPostElectionView(TestCase):
    def setUp(self):
        self.post_election = PostElectionFactory(
            election__election_date="2017-03-23"
        )

    def test_results_table(self):
        """check that the table containing the electorate,
        turnout, spoilt ballots, ballot papers exist
        for past elections"""

        self.post_election.electorate = 100
        self.post_election.spoilt_ballots = 5
        self.post_election.save()
        response = self.client.get(
            self.post_election.get_absolute_url(), follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.post_election.has_results)
        self.assertContains(response, "Electorate")
        self.assertNotContains(response, "Turnout")
        self.assertContains(response, "Spoilt Ballots")
        self.assertNotContains(response, "Ballot Papers Issued")


class TestPostElectionsToPeopleMixin(TestCase):
    def test_people_for_ballot_ordered_alphabetically(self):
        people = [
            {"name": "Jane Adams", "sort_name": "Adams"},
            {"name": "John Middle", "sort_name": None},
            {"name": "Jane Smith", "sort_name": "Smith"},
        ]
        post_election = PostElectionFactory()
        shuffle(people)
        for person in people:
            PersonPostFactory(
                post_election=post_election,
                election=post_election.election,
                post=post_election.post,
                person__name=person["name"],
                person__sort_name=person["sort_name"],
            )
        candidates = list(
            PostelectionsToPeopleMixin().people_for_ballot(post_election)
        )
        self.assertEqual(candidates[0].person.name, "Jane Adams")
        self.assertEqual(candidates[1].person.name, "John Middle")
        self.assertEqual(candidates[2].person.name, "Jane Smith")


class TestPostelectionsToPeopleMixin(TestCase):
    # should be updated as more queries are added
    PERSON_POST_QUERY = 1
    PLEDGE_QUERY = 1
    LEAFLET_QUERY = 1
    PREVIOUS_PARTY_AFFILIATIONS_QUERY = 1
    ALL_QUERIES = [
        PERSON_POST_QUERY,
        PLEDGE_QUERY,
        LEAFLET_QUERY,
        PREVIOUS_PARTY_AFFILIATIONS_QUERY,
    ]

    def setUp(self):
        self.post_election = PostElectionFactory()
        self.candidates = PersonPostWithPartyFactory.create_batch(
            size=10,
            post_election=self.post_election,
            election=self.post_election.election,
        )
        self.mixin = PostelectionsToPeopleMixin()

    def test_num_queries_previous_party_affiliations(self):
        """
        Test with lots of previous party affiliations, number of
        queries is consistent
        """
        for candidate in self.candidates:
            old_parties = PartyFactory.create_batch(
                size=10, party_id=factory.Sequence(lambda n: f"PP{n}")
            )
            candidate.previous_party_affiliations.set(old_parties)

        with self.assertNumQueries(sum(self.ALL_QUERIES)):
            queryset = self.mixin.people_for_ballot(self.post_election)
            previous_parties = []
            for candidate in queryset:
                party_ids = [
                    party.party_id
                    for party in candidate.previous_party_affiliations.all()
                ]
                previous_parties += party_ids

            candidates = list(queryset)
            self.assertEqual(len(candidates), 10)
            self.assertEqual(len(previous_parties), 10 * 10)

    def test_num_queries_using_compact(self):
        """
        Test when using compact number of queries is one less
        """
        all_queries_without_pledge = self.ALL_QUERIES.copy()
        all_queries_without_pledge.remove(self.PLEDGE_QUERY)
        with self.assertNumQueries(sum(all_queries_without_pledge)):
            queryset = self.mixin.people_for_ballot(
                self.post_election, compact=True
            )
            # resolve queryset to execute the queries
            candidates = list(queryset)
            self.assertEqual(len(candidates), 10)
