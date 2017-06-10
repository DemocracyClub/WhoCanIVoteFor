from django.test import TestCase

from people.tests.factories import PersonFactory, PersonPostFactory
from parties.tests.factories import PartyFactory
from elections.tests.factories import ElectionFactory



class PersonViewTests(TestCase):
    def setUp(self):
        self.party = PartyFactory()
        self.person = PersonFactory()
        self.person_url = self.person.get_absolute_url()

    def test_person_view(self):
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'people/person_detail.html')


    def test_correct_elections_listed(self):
        response = self.client.get(self.person_url, follow=True)

        election_name = "FooBar Election 2017"

        self.assertNotContains(response, election_name)
        election = ElectionFactory(
            name=election_name,
            current=True,
            election_date="2040-01-01",
            slug="foobar")
        PersonPostFactory(
            election=election,
            person=self.person,
            party=self.party,
        )

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, election_name)
        self.assertContains(response, "is the")

    def test_election_in_past_listed(self):
        response = self.client.get(self.person_url, follow=True)

        election_name = "FooBar Election 2017"

        self.assertNotContains(response, election_name)
        election = ElectionFactory(
            name=election_name,
            current=True,
            election_date="2017-01-01",
            slug="foobar")
        PersonPostFactory(
            election=election,
            person=self.person,
            party=self.party,
        )

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, election_name)
        self.assertContains(response, "was the")
