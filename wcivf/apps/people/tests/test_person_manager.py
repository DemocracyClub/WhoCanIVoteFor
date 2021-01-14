import pytest

from django.test import TestCase
from django.utils import timezone

from people.models import Person, PersonPost
from people.tests.factories import PersonFactory, PersonPostFactory
from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
    ElectionFactoryLazySlug,
)


class PersonManagerTests(TestCase):
    def setUp(self):
        self.election = ElectionFactory()
        self.post = PostFactory()
        self.pe = PostElectionFactory(election=self.election, post=self.post)
        people = [PersonFactory() for p in range(5)]
        for person in people:
            PersonPostFactory(
                post_election=self.pe,
                election=self.election,
                post=self.post,
                person=person,
            )

    def test_counts_by_post(self):
        assert Person.objects.all().count() == 5
        assert PersonPost.objects.all().counts_by_post().count() == 1


@pytest.mark.freeze("2022-01-13")
class PersonPostManagerTests(TestCase):
    def setUp(self):
        # create some Election objects with different dates
        future_election = ElectionFactoryLazySlug(
            election_date=timezone.datetime(2021, 5, 6),
        )
        past_election = ElectionFactoryLazySlug(
            election_date=timezone.datetime(2017, 6, 8)
        )

        # create the Post object (division) with the above elections
        post = PostFactory(elections=[future_election, past_election])

        # create a ballot like object for each of the elections
        future_post_election = PostElectionFactory(
            election=future_election,
            post=post,
        )
        past_post_election = PostElectionFactory(
            election=past_election,
            post=post,
        )

        # create the 'candidacy' like objects
        self.in_future = PersonPostFactory(
            election=future_election,
            post=post,
            post_election=future_post_election,
        )
        self.in_past = PersonPostFactory(
            election=past_election,
            post=post,
            post_election=past_post_election,
        )

    def test_future(self):
        qs = PersonPost.objects.future()
        assert qs.count() == 1
        self.assertIn(self.in_future, qs)
        self.assertNotIn(self.in_past, qs)

    def test_past(self):
        qs = PersonPost.objects.past()
        assert qs.count() == 1
        self.assertIn(self.in_past, qs)
        self.assertNotIn(self.in_future, qs)
