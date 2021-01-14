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
            election_date=timezone.datetime(2021, 5, 6)
        )
        past_current_election = ElectionFactoryLazySlug(
            current=True, election_date=timezone.datetime(2021, 1, 1)
        )
        past_not_current = ElectionFactoryLazySlug(
            current=False, election_date=timezone.datetime(2017, 6, 8)
        )

        # create the 'candidacy' like objects
        self.in_future = PersonPostFactory(election=future_election)
        self.in_past_current = PersonPostFactory(election=past_current_election)
        self.in_past_not_current = PersonPostFactory(election=past_not_current)

    def test_current_or_future(self):
        qs = PersonPost.objects.current_or_future()
        assert qs.count() == 2
        self.assertIn(self.in_future, qs)
        self.assertIn(self.in_past_current, qs)
        self.assertNotIn(self.in_past_not_current, qs)

    def test_past_not_current(self):
        qs = PersonPost.objects.past_not_current()
        assert qs.count() == 1
        self.assertIn(self.in_past_not_current, qs)
        self.assertNotIn(self.in_future, qs)
        self.assertNotIn(self.in_past_current, qs)

    def test_current(self):
        qs = PersonPost.objects.current()
        assert qs.count() == 2
        self.assertIn(self.in_future, qs)
        self.assertIn(self.in_past_current, qs)
        self.assertNotIn(self.in_past_not_current, qs)
