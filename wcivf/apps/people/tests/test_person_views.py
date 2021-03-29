from unittest.mock import MagicMock

import pytest
from django.test import TestCase
from django.test.utils import override_settings
from elections.tests.factories import (
    ElectionFactory,
    ElectionFactoryLazySlug,
    PostElectionFactory,
    PostFactory,
)
from parties.tests.factories import LocalPartyFactory, PartyFactory
from people.tests.factories import PersonFactory, PersonPostFactory
from people.views import PersonView


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class PersonViewTests(TestCase):
    def setUp(self):
        self.party = PartyFactory()
        self.person = PersonFactory()
        self.person_url = self.person.get_absolute_url()

    def test_current_person_view(self):
        self.personpost = PersonPostFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "people/person_detail.html")
        self.assertNotContains(
            response, '<meta name="robots" content="noindex">'
        )

    def test_not_current_person_view(self):
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "people/not_current_person_detail.html"
        )
        self.assertContains(response, f"{ self.person.name} stood for election")
        self.assertNotContains(response, f"{ self.person.name} Online")
        self.assertContains(response, '<meta name="robots" content="noindex">')

    def test_not_current_person_with_twfy_id(self):
        self.person.twfy_id = 10999
        self.person.save()
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "people/person_detail.html")
        self.assertNotContains(
            response, '<meta name="robots" content="noindex">'
        )
        self.assertContains(response, "Record in office")
        self.assertContains(response, "TheyWorkForYou")

    def test_correct_elections_listed(self):
        response = self.client.get(self.person_url, follow=True)

        election_name = "FooBar Election 2017"

        self.assertNotContains(response, election_name)
        election = ElectionFactory(
            name=election_name,
            current=True,
            election_date="2040-01-01",
            slug="local.foobar.2040-01-01",
        )
        post = PostFactory()
        pe = PostElectionFactory(
            election=election,
            post=post,
            ballot_paper_id="local.foo.bar.2040-01-01",
        )
        PersonPostFactory(
            post_election=pe,
            election=election,
            person=self.person,
            party=self.party,
        )

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, election_name)
        self.assertContains(response, "is a")

    def test_election_in_past_listed(self):
        response = self.client.get(self.person_url, follow=True)

        election_name = "FooBar Election 2017"

        self.assertNotContains(response, election_name)
        election = ElectionFactory(
            name=election_name,
            current=False,
            election_date="2017-01-01",
            slug="local.foobar.2017-01-01",
        )
        post = PostFactory()
        pe = PostElectionFactory(
            election=election,
            post=post,
            ballot_paper_id="local.foo.bar.2017-01-01",
        )
        PersonPostFactory(
            post_election=pe,
            election=election,
            person=self.person,
            party=self.party,
        )

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, election_name)
        self.assertContains(response, "was a")

    def test_multiple_candidacies_intro(self):
        election_one = ElectionFactory()
        election_two = ElectionFactoryLazySlug()
        party = PartyFactory(party_name="Liberal Democrat", party_id="foo")
        PersonPostFactory(
            person=self.person, election=election_one, party=party
        )
        PersonPostFactory(
            person=self.person, election=election_two, party=party
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertContains(
            response,
            "is a Liberal Democrat candidate in the following elections:",
        )

    def test_multiple_independent_candidacies_intro(self):
        election_one = ElectionFactory()
        election_two = ElectionFactoryLazySlug()
        party = PartyFactory(party_name="Independent", party_id="ynmp-party:2")
        PersonPostFactory(
            person=self.person, election=election_one, party=party
        )
        PersonPostFactory(
            person=self.person, election=election_two, party=party
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertContains(
            response, "is an Independent candidate in the following elections:"
        )

    def test_one_candidacy_intro(self):
        election = ElectionFactory()
        party = PartyFactory(
            party_name="Conservative and Unionist Party", party_id="ConUnion"
        )
        person_post = PersonPostFactory(
            person=self.person, election=election, party=party
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertContains(
            response,
            f"{self.person.name} is a {party.party_name} candidate in {person_post.post.label} in the {election.name}.",
        )

    def test_no_previous_elections(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Previous Elections")

    def test_previous_elections(self):
        past_election = ElectionFactoryLazySlug(
            election_date="2019-05-02", current=False
        )
        party = PartyFactory(party_name="Liberal Democrat", party_id="foo")
        PersonPostFactory(
            person=self.person,
            post_election__election=past_election,
            election=past_election,
            party=party,
            votes_cast=1000,
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertContains(response, "Previous Elections")

    def test_no_statement_to_voters(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Statement to voters")

    def test_statement_to_voters(self):
        self.person.statement_to_voters = "I believe in equal rights."
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Statement to voters")

    def test_no_TWFY(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Record in office")

    def test_TWFY(self):
        self.person.twfy_id = 123
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Record in office")

    def test_no_wikipedia(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Wikipedia")

    def test_wikipedia(self):
        self.person.wikipedia_bio = "yo"
        self.person.wikipedia_url = "https//www.wikipedia.com/yo"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Wikipedia")

    def test_no_facebook(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "username")

    def test_facebook(self):
        self.person.facebook_personal_url = "https//www.facebook.com/yo"
        self.person.facebook_page_url = "https//www.facebook.com/yo"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "yo")

    def test_no_linkedin(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "LinkedIn")

    def test_linkedin(self):
        self.person.linkedin_url = "https://www.linkedin.com/yo"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "LinkedIn")

    def test_instagram(self):
        self.person.instagram_url = "https://www.instagram.com/yo"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Instagram")

    def test_no_instagram(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Instagram")

    def test_party_page(self):
        self.person.party_ppc_page_url = "https://www.voteforme.com/bob"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(
            response, "The party's candidate page for this person"
        )

    def test_no_party_page(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(
            response, "The party's candidate page for this person"
        )

    def test_no_youtube(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "YouTube")

    def test_youtube(self):
        self.person.youtube_profile = "Mary123"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "YouTube")

    def test_email(self):
        self.person.email = "me@voteforme.com"
        self.person.save()
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Email")

    def test_no_email(self):
        PersonPostFactory(person=self.person, election=ElectionFactory())
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Email")

    def test_local_party_for_local_election(self):
        party = PartyFactory(party_name="Labour Party", party_id="party:53")
        local_party = LocalPartyFactory(
            name="Derbyshire Labour", is_local=True, parent=party
        )
        PersonPostFactory(
            person=self.person,
            election=ElectionFactory(),
            party=party,
        )
        response = self.client.get(self.person_url, follow=True)
        expected = f"{self.person.name}'s local party is {local_party.label}."
        self.assertContains(response, expected)

    def test_local_party_for_non_local_election(self):
        party = PartyFactory(party_name="Labour Party", party_id="party:53")
        local_party = LocalPartyFactory(
            name="Welsh Labour | Llafur Cymru", is_local=False, parent=party
        )
        PersonPostFactory(
            person=self.person,
            election=ElectionFactory(),
            party=party,
        )
        response = self.client.get(self.person_url, follow=True)
        expected = f"{self.person.name} is a {local_party.label} candidate."
        self.assertContains(response, expected)


class TestPersonViewUnitTests:
    @pytest.fixture
    def view_obj(self, rf):
        """
        Return an instance of PersonView set up with a fake request object
        """
        request = rf.get("/person/1/")
        view = PersonView()
        view.setup(request=request)
        return view

    @pytest.mark.parametrize(
        "object, expected",
        [
            (MagicMock(twfy_id=10999), "people/person_detail.html"),
            (
                MagicMock(current_or_future_candidacies=True),
                "people/person_detail.html",
            ),
            (
                MagicMock(current_or_future_candidacies=False, twfy_id=None),
                "people/not_current_person_detail.html",
            ),
        ],
    )
    def test_get_template_names(self, view_obj, object, expected):
        view_obj.object = object
        assert view_obj.get_template_names() == [expected]
