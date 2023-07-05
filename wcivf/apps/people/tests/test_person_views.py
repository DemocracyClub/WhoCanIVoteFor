from unittest.mock import MagicMock
from django.utils.html import strip_tags
from freezegun import freeze_time

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
from people.tests.factories import (
    PersonFactory,
    PersonPostFactory,
    PersonPostWithPartyFactory,
)
from people.views import PersonView
from people.tests.helpers import create_person


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
        self.personpost = PersonPostWithPartyFactory(
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
            person=self.person,
            election=election_one,
            party=party,
            party_name=party.party_name,
        )
        PersonPostFactory(
            person=self.person,
            election=election_two,
            party=party,
            party_name=party.party_name,
        )
        response = self.client.get(self.person_url, follow=True)
        expected = "is a Liberal Democrat candidate in the following elections:"
        self.assertContains(response, expected)

    def test_multiple_independent_candidacies_intro(self):
        election_one = ElectionFactory()
        election_two = ElectionFactoryLazySlug()
        party = PartyFactory(party_name="Independent", party_id="ynmp-party:2")
        PersonPostFactory(
            person=self.person,
            election=election_one,
            party=party,
            party_name=party.party_name,
        )
        PersonPostFactory(
            person=self.person,
            election=election_two,
            party=party,
            party_name=party.party_name,
        )
        response = self.client.get(self.person_url, follow=True)
        expected = "is an Independent candidate in the following elections:"
        self.assertContains(response, expected)

    def test_one_candidacy_intro(self):
        election = ElectionFactory()
        party = PartyFactory(
            party_name="Conservative and Unionist Party", party_id="ConUnion"
        )
        person_post = PersonPostFactory(
            person=self.person,
            election=election,
            party=party,
            party_name=party.party_name,
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertContains(
            response,
            f"{self.person.name} is a {person_post.party_name} candidate in {person_post.post.label} constituency in the {election.nice_election_name}.",
        )

    def test_previous_party_affiliations_in_current_elections(self):
        """This is a test for previous party affiliations in the
        person intro"""

        election = ElectionFactory(
            name="Welsh Assembly Election",
            current=True,
            election_date="2022-05-01",
            slug="local.welsh.assembly.2022-05-01",
        )
        party = PartyFactory(
            party_name="Conservative and Unionist Party", party_id="ConUnion"
        )
        post = PostFactory(label="Welsh Assembly", territory="WLS")
        pe = PostElectionFactory(
            election=election,
            post=post,
            ballot_paper_id="local.welsh.assembly.2022-05-01",
        )
        person_post = PersonPostFactory(
            person=self.person,
            election=election,
            party=party,
            party_name=party.party_name,
            post=post,
            post_election=pe,
        )

        previous_party_1 = PartyFactory(
            party_name="Conservative", party_id="foo_id"
        )
        previous_party_2 = PartyFactory(party_name="Labour", party_id="bar_id")
        person_post.previous_party_affiliations.add(previous_party_1)
        person_post.previous_party_affiliations.add(previous_party_2)
        self.assertEqual(person_post.previous_party_affiliations.count(), 2)
        self.assertEqual(self.person.current_or_future_candidacies.count(), 1)
        response = self.client.get(self.person_url, follow=True)

        self.assertTemplateUsed(
            "elections/includes/_previous_party_affiliations.html"
        )
        self.assertTemplateUsed("people/includes/_person_intro_card.html")

        self.assertContains(
            response,
            "has declared their affiliation with the following parties in the past 12 months",
        )

    def test_no_previous_party_affiliations(self):
        election = ElectionFactory(
            name="Welsh Assembly Election",
            current=True,
            election_date="2022-05-01",
            slug="local.welsh.assembly.2022-05-01",
        )
        party = PartyFactory(
            party_name="Conservative and Unionist Party", party_id="ConUnion"
        )
        post = PostFactory(label="Welsh Assembly", territory="WLS")
        pe = PostElectionFactory(
            election=election,
            post=post,
            ballot_paper_id="local.welsh.assembly.2022-05-01",
        )
        person_post = PersonPostFactory(
            person=self.person,
            election=election,
            party=party,
            party_name=party.party_name,
            post=post,
            post_election=pe,
        )

        self.assertEqual(person_post.previous_party_affiliations.count(), 0)
        self.assertEqual(self.person.current_or_future_candidacies.count(), 1)
        response = self.client.get(self.person_url, follow=True)

        self.assertTemplateNotUsed(
            "elections/includes/_previous_party_affiliations.html"
        )
        self.assertTemplateUsed("people/includes/_person_intro_card.html")

        self.assertNotContains(
            response,
            "has declared their affiliation with the following parties in the past 12 months",
        )

    def test_previous_party_affiliations_in_past_elections_table(self):
        """This is a test for current previous party affiliations in the
        previous elections table"""

        past_election = ElectionFactory(
            name="Welsh Local Election",
            current=False,
            election_date="2021-05-01",
            slug="local.welsh.assembly.2021-05-01",
        )
        party = PartyFactory(
            party_name="Conservative and Unionist Party", party_id="ConUnion"
        )
        past_person_post = PersonPostFactory(
            person=self.person,
            post_election__election=past_election,
            election=past_election,
            party=party,
            votes_cast=1000,
        )
        previous_party_1 = PartyFactory(
            party_name="Conservative", party_id="foo_id"
        )
        previous_party_2 = PartyFactory(party_name="Labour", party_id="bar_id")
        past_person_post.previous_party_affiliations.add(previous_party_1)
        past_person_post.previous_party_affiliations.add(previous_party_2)

        response = self.client.get(self.person_url, follow=True)

        self.assertEqual(self.person.past_not_current_candidacies.count(), 1)
        self.assertTemplateUsed(
            "people/includes/_person_previous_elections_card.html"
        )
        self.assertTemplateUsed(
            "elections/includes/_previous_party_affiliations.html"
        )
        self.assertContains(
            response,
            "Other party affiliations in the past 12 months",
            html=True,
        )
        self.assertContains(response, "Conservative, Labour", html=True)

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
        self.assertContains(response, f"{self.person.name}'s Elections")

    def test_no_statement_to_voters(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Statement to voters")

    def test_statement_to_voters(self):
        self.person.statement_to_voters = "I believe in equal rights."
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Statement to voters")

    def test_no_TWFY(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Record in office")

    def test_TWFY(self):
        self.person.twfy_id = 123
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Record in office")

    def test_no_wikipedia(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Wikipedia")

    def test_wikipedia(self):
        self.person.wikipedia_bio = "yo"
        self.person.wikipedia_url = "https//www.wikipedia.com/yo"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Wikipedia")

    def test_no_facebook(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "username")

    def test_facebook(self):
        self.person.facebook_personal_url = "https//www.facebook.com/yo"
        self.person.facebook_page_url = "https//www.facebook.com/yo"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "yo")

    def test_no_linkedin(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "LinkedIn")

    def test_linkedin(self):
        self.person.linkedin_url = "https://www.linkedin.com/yo"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "LinkedIn")

    def test_instagram(self):
        self.person.instagram_url = "https://www.instagram.com/yo"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Instagram")

    def test_no_instagram(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Instagram")

    def test_no_blog_url(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, f"{ self.person.name }'s Blog")

    def test_blog_url(self):
        self.person.blog_url = "https://www.bloglovin.com/john"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, f"{ self.person.name }'s blog")

    def test_party_page(self):
        self.person.party_ppc_page_url = "https://www.voteforme.com/bob"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
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
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "YouTube")

    def test_youtube(self):
        self.person.youtube_profile = "Mary123"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "YouTube")

    def test_email(self):
        self.person.email = "me@voteforme.com"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Email")

    def test_no_email(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "<dt>Email</dt>")

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

    def test_person_detail_404_with_string_pk(self):
        """
        Regression test to ensure non-int person IDs raise a 404 not a 500
        """
        req = self.client.get("/person/partywebsite.org/")
        self.assertEqual(req.status_code, 404)


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


@freeze_time("2021-04-15")
class TestPersonIntro(TestCase):
    def setUp(self):
        self.current_candidate = create_person(current=True)
        self.current_deceased = create_person(current=True, deceased=True)
        self.past_candidate = create_person(current=False)
        self.past_deceased = create_person(current=False, deceased=False)
        self.independent_candidate = create_person(
            current=True, party_name="Independent"
        )
        self.independent_candidate_past = create_person(
            current=False, party_name="Independent"
        )
        self.speaker = create_person(
            current=True,
            party_name="Speaker seeking re-election",
            election_name="UK General Election",
        )
        self.speaker_past = create_person(
            current=False,
            party_name="Speaker seeking re-election",
            election_name="UK General Election",
        )
        parl_election = ElectionFactory(
            current=True,
            election_date="2023-05-11",
            name="UK General Election 2023",
            slug="parl.2023",
        )
        self.parliamentary_candidate = PersonPostWithPartyFactory(
            person__name="Joe Bloggs",
            election=parl_election,
            post_election__election=parl_election,
            post__label="Hallam",
            post__ynr_id="hallam",
        )
        mayoral_election = ElectionFactory(
            current=True,
            election_date="2021-05-06",
            name="Mayor of Bristol",
            slug="mayor.bristol.2021-05-06",
        )
        self.mayoral_candidate = PersonPostWithPartyFactory(
            person__name="Joe Bloggs",
            election=mayoral_election,
            post_election__election=mayoral_election,
            post_election__ballot_paper_id="mayor.bristol.2021-05-06",
            post__ynr_id="mayor-of-bristol",
        )
        self.candidate_with_votes_unelected = create_person(
            current=False, votes_cast=10000, elected=False
        )
        self.candidate_with_votes_elected = create_person(
            current=False, votes_cast=10000, elected=True
        )
        self.pcc_candidate = create_person(
            election_type="pcc",
            election_name="Police and Crime Commissioner for South Yorkshire",
        )
        self.list_candidate = create_person(
            election_type="gla.a",
            list_election=True,
            list_position=1,
            election_name="London Assembly elections (additional)",
        )

    def test_intro_in_view(self):
        """This test checks for the presence of text
        in the meta tags"""
        candidacies = [
            (
                self.current_candidate,
                "Joe Bloggs is a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.current_deceased,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.past_candidate,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.past_deceased,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.independent_candidate,
                "Joe Bloggs is an independent candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.independent_candidate_past,
                "Joe Bloggs was an independent candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.speaker,
                "Joe Bloggs is the Speaker seeking re-election in Ecclesall constituency in the UK General Election",
            ),
            (
                self.speaker_past,
                "Joe Bloggs was the Speaker seeking re-election in Ecclesall constituency in the UK General Election",
            ),
            (
                self.parliamentary_candidate,
                "Joe Bloggs is a Test Party candidate in Hallam constituency in the UK General Election 2023.",
            ),
            (
                self.mayoral_candidate,
                "Joe Bloggs is the Test Party candidate for Mayor of Bristol.",
            ),
            (
                self.candidate_with_votes_unelected,
                "They received 10,000 votes.",
            ),
            (
                self.candidate_with_votes_elected,
                "They were elected with 10,000 votes.",
            ),
            (
                self.pcc_candidate,
                "Joe Bloggs is the Test Party candidate for Police and Crime Commissioner for South Yorkshire.",
            ),
            (
                self.list_candidate,
                "Joe Bloggs is the 1st place candidate for the Test Party in the London Assembly elections (additional).",
            ),
        ]
        for candidacy in candidacies:
            with self.subTest(msg=candidacy[1]):
                person = candidacy[0].person
                expected = candidacy[1]
                response = self.client.get(person.get_absolute_url())

                self.assertContains(response, expected)

                if " is " in expected:
                    expected = expected.replace(" is ", " was ")
                    person.death_date = "2020-01-01"
                    response = self.client.get(person.get_absolute_url())

    def test_intro_method(self):
        """
        Test the exact string returned by the into method
        """
        candidacies = [
            (
                self.current_candidate,
                "Joe Bloggs is a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.current_deceased,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.past_candidate,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.past_deceased,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.independent_candidate,
                "Joe Bloggs is an independent candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.independent_candidate_past,
                "Joe Bloggs was an independent candidate in Ecclesall in the Sheffield local election.",
            ),
            (
                self.speaker,
                "Joe Bloggs is the Speaker seeking re-election in Ecclesall constituency in the UK General Election.",
            ),
            (
                self.speaker_past,
                "Joe Bloggs was the Speaker seeking re-election in Ecclesall constituency in the UK General Election.",
            ),
            (
                self.parliamentary_candidate,
                "Joe Bloggs is a Test Party candidate in Hallam constituency in the UK General Election 2023.",
            ),
            (
                self.mayoral_candidate,
                "Joe Bloggs is the Test Party candidate for Mayor of Bristol.",
            ),
            (
                self.candidate_with_votes_unelected,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election. They received 10,000 votes.",
            ),
            (
                self.candidate_with_votes_elected,
                "Joe Bloggs was a Test Party candidate in Ecclesall in the Sheffield local election. They were elected with 10,000 votes.",
            ),
            (
                self.pcc_candidate,
                "Joe Bloggs is the Test Party candidate for Police and Crime Commissioner for South Yorkshire.",
            ),
            (
                self.list_candidate,
                "Joe Bloggs is the 1st place candidate for the Test Party in the London Assembly elections (additional).",
            ),
        ]

        for candidacy in candidacies:
            with self.subTest(msg=candidacy[1]):
                person = candidacy[0].person
                expected = candidacy[1]
                intro = strip_tags(person.intro)
                intro = intro.replace("\n", "")
                intro = intro.strip()
                intro = " ".join(intro.split())
                self.assertEqual(intro, expected)
                self.assertEqual(person.text_intro, expected)
