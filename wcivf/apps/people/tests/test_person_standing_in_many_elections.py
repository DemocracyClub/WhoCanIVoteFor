from django.test import TestCase

from people.tests.factories import PersonFactory, PersonPostFactory
from elections.tests.factories import (
    ElectionFactory,
    PostFactory,
    PostElectionFactory,
)


class TestPersonInMultipleElections(TestCase):
    def test_more_than_one_election(self):
        person = PersonFactory()
        election1 = ElectionFactory()
        election2 = ElectionFactory(slug="parl.2010")
        post1 = PostFactory()
        post2 = PostFactory(ynr_id="WMC:E14000645", label="Southwark")

        pe1 = PostElectionFactory(election=election1, post=post1)
        pe2 = PostElectionFactory(election=election2, post=post2)

        PersonPostFactory(
            person=person, post_election=pe1, post=post1, election=election1
        )

        PersonPostFactory(
            post_election=pe2, person=person, election=election2, post=post2
        )

        assert person.personpost_set.all().count() == 2
