from unittest.mock import MagicMock

import pytest
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.html import strip_tags
from elections.models import VotingSystem
from elections.tests.factories import (
    ElectionFactory,
    ElectionWithPostFactory,
    PostElectionFactory,
    PostFactory,
)
from freezegun import freeze_time
from parties.tests.factories import (
    # LocalPartyFactory,
    NationalPartyFactory,
    PartyFactory,
)
from people.tests.factories import (
    PersonFactory,
    PersonPostFactory,
    PersonPostWithPartyFactory,
)
from people.tests.helpers import create_person
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
        self.assertContains(response, f"{self.person.name}")
        self.assertContains(response, "stood for election")
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
        self.assertContains(response, "stood for election")
        self.assertContains(response, "once")
        self.assertNotContains(response, "times")

    def test_multiple_candidacies_intro(self):
        election_one = ElectionFactory(
            election_date="2040-02-01",
            current=True,
            name="FooBar Election 2040",
            slug="local.foobar.2040-02-01",
        )
        election_two = ElectionFactory(
            election_date="2040-01-01",
            current=True,
            name="FooBar Election 2040",
            slug="local.foobar.2040-01-01",
        )
        election_three = ElectionFactory(
            election_date="2015-01-01",
            current=False,
            name="FooBar Election 2015",
            slug="local.foobar.2015-01-01",
        )
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
        PersonPostFactory(
            person=self.person,
            election=election_three,
            party=party,
            party_name=party.party_name,
        )
        self.assertEqual(self.person.future_candidacies.count(), 2)
        response = self.client.get(self.person_url, follow=True)
        expected = """is a <a href="/parties/foo/liberal-democrat">Liberal Democrat</a> candidate in the following elections:"""
        self.assertContains(response, expected)

    def test_multiple_independent_candidacies_intro(self):
        election_one = ElectionFactory(
            election_date="2040-02-01",
            current=True,
            name="FooBar Election 2040",
            slug="local.foobar.2040-02-01",
        )
        election_two = ElectionFactory(
            election_date="2040-01-01",
            current=True,
            name="FooBar Election 2040",
            slug="local.foobar.2040-01-01",
        )
        election_three = ElectionFactory(
            election_date="2015-01-01",
            current=False,
            name="FooBar Election 2015",
            slug="local.foobar.2015-01-01",
        )
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
        PersonPostFactory(
            person=self.person,
            election=election_three,
            party=party,
            party_name=party.party_name,
        )
        self.assertEqual(self.person.future_candidacies.count(), 2)
        response = self.client.get(self.person_url, follow=True)
        expected = """is an <a href="/parties/ynmp-party:2/independent">Independent</a> candidate in the following elections:"""
        self.assertContains(response, expected)

    def test_one_candidacy_intro(self):
        election = ElectionFactory()
        party = PartyFactory(
            party_name="Conservative and Unionist Party", party_id="ConUnion"
        )
        PersonPostFactory(
            person=self.person,
            election=election,
            party=party,
            party_name=party.party_name,
        )
        self.assertTrue(election.in_past)
        self.assertEqual(self.person.future_candidacies.count(), 0)
        self.assertEqual(self.person.current_or_future_candidacies.count(), 1)
        response = self.client.get(self.person_url, follow=True)
        self.assertContains(
            response,
            "was a Conservative and Unionist Party candidate in",
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

    def test_previous_elections_card(self):
        """Test that the postcode search results have a
        table of previous elections. In that table, the
        election name, date and slug should be displayed
        as well as vote count, position and party for each
        ballot for the candidate
        """
        past_election = ElectionFactory(
            name="Welsh Assembly Election",
            current=False,
            election_date="2021-05-01",
            slug="local.welsh.assembly.2021-05-01",
        )
        past_post_election = PostElectionFactory(
            election=past_election,
            post=PostFactory(label="Welsh Assembly", territory="WLS"),
            ballot_paper_id="local.welsh.assembly.2021-05-01",
            voting_system=VotingSystem(slug="FPTP"),
        )
        party = PartyFactory(
            party_name="Conservative and Unionist Party",
            party_id="party:52",
        )
        PersonPostFactory(
            person=self.person,
            post_election=past_post_election,
            election=past_election,
            party=party,
            votes_cast=1000,
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertTemplateUsed(
            "people/includes/_person_previous_elections_card.html"
        )
        self.assertContains(response, "2021")
        self.assertContains(response, "Welsh Assembly: Welsh Assembly Election")
        self.assertContains(response, "1,000 votes (not elected)")
        self.assertContains(response, """1st / 1 candidate""")

    def test_previous_elections_card_for_STV(self):
        """Test that the postcode search results have a
        table of previous elections with the text:
        'We do not collect voting data for
        Single Transferable Vote election.'"""
        past_election = ElectionFactory(
            name="Welsh Assembly Election",
            current=False,
            election_date="2021-05-01",
            slug="local.welsh.assembly.2021-05-01",
            voting_system=VotingSystem(slug="STV"),
        )

        past_post_election = PostElectionFactory(
            election=past_election,
            post=PostFactory(label="Welsh Assembly", territory="WLS"),
            ballot_paper_id="local.welsh.assembly.2021-05-01",
        )
        party = PartyFactory(party_name="Liberal Democrat", party_id="foo")
        PersonPostFactory(
            person=self.person,
            post_election=past_post_election,
            election=past_election,
            party=party,
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertTemplateUsed(
            "people/includes/_person_previous_elections_card.html"
        )
        self.assertContains(
            response,
            """We do not collect voting data for Single Transferable Vote elections.""",
            html=True,
        )

    def test_previous_elections_card_for_sv(self):
        """Test that the postcode search results have a
        table of previous elections with the text:
        "We do not collect voting data for Supplementary Vote elections."
        """
        past_election = ElectionFactory(
            name="Welsh Assembly Election",
            current=False,
            election_date="2021-05-01",
            slug="local.welsh.assembly.2021-05-01",
            voting_system=VotingSystem(slug="sv"),
        )
        past_post_election = PostElectionFactory(
            election=past_election,
            post=PostFactory(label="Welsh Assembly", territory="WLS"),
            ballot_paper_id="local.welsh.assembly.2021-05-01",
        )
        party = PartyFactory(party_name="Liberal Democrat", party_id="foo")
        PersonPostFactory(
            person=self.person,
            post_election=past_post_election,
            election=past_election,
            party=party,
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertTemplateUsed(
            "people/includes/_person_previous_elections_card.html"
        )
        self.assertContains(
            response,
            """We do not collect voting data for Supplementary Vote elections.""",
            html=True,
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

    def test_no_statement_to_voters(self):
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertNotContains(response, "Statement to voters")

    def test_statement_to_voters(self):
        self.person.statement_to_voters = "I believe in equal rights."

        self.person.statement_to_voters_last_updated = "2021-04-15"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Statement to voters")
        self.assertContains(
            response, "This statement was last updated on April 15, 2021"
        )

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

    def test_not_current_about_section(self):
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(
            response.template_name, ["people/not_current_person_detail.html"]
        )
        self.assertNotEqual(
            response.template_name, ["people/person_about_card.html"]
        )
        self.assertNotContains(response, "About Candidate 24")

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
        assert b"<dt>LinkedIn</dt>" not in response.content

    def test_linkedin(self):
        self.person.linkedin_url = "https://www.linkedin.com/in/yo"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        assert b"<dt>LinkedIn</dt>" in response.content

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
        self.assertIn("YouTube", response.content.decode("utf8"))

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

    def test_tiktok(self):
        self.person.tiktok_url = "https://www.tiktok.com/@voteforme"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "TikTok")

    def test_bluesky(self):
        self.person.blue_sky_url = "https://www.bluesky.com/voteforme"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "BlueSky")

    def test_threads(self):
        self.person.threads_url = "https://www.threads.com/voteforme"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "Threads")

    def test_other_url(self):
        self.person.other_url = "https://www.other.com/voteforme"
        self.person.save()
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertEqual(response.template_name, ["people/person_detail.html"])
        self.assertContains(response, "other contact info")

    # def test_local_party_for_local_election(self):
    #     party = PartyFactory(party_name="Labour Party", party_id="party:53")
    #     local_party = LocalPartyFactory(
    #         name="Derbyshire Labour", is_local=True, parent=party
    #     )
    #     PersonPostFactory(
    #         person=self.person,
    #         election=ElectionFactory(),
    #         party=party,
    #     )
    #     response = self.client.get(self.person_url, follow=True)
    #     expected = f"{self.person.name}'s local party is {local_party.label}."
    #     self.assertContains(response, expected)

    # def test_local_party_for_non_local_election(self):
    #     party = PartyFactory(party_name="Labour Party", party_id="party:53")
    #     local_party = LocalPartyFactory(
    #         name="Welsh Labour | Llafur Cymru", is_local=False, parent=party
    #     )
    #     PersonPostFactory(
    #         person=self.person,
    #         election=ElectionFactory(),
    #         party=party,
    #     )
    #     response = self.client.get(self.person_url, follow=True)
    #     expected = f"{self.person.name} is a {local_party.label} candidate."
    #     self.assertContains(response, expected)

    def test_national_party_for_general_election(self):
        party = PartyFactory(party_name="Labour Party", party_id="party:53")
        national_party = NationalPartyFactory(
            name="Labour Party", parent=party, is_national=True
        )
        PersonPostFactory(
            person=self.person,
            election=ElectionFactory(),
            party=party,
        )
        response = self.client.get(self.person_url, follow=True)
        expected = f"{self.person.name}'s party is {national_party.label}."
        self.assertContains(response, expected)

    def test_person_detail_404_with_string_pk(self):
        """
        Regression test to ensure non-int person IDs raise a 404 not a 500
        """
        req = self.client.get("/person/partywebsite.org/")
        self.assertEqual(req.status_code, 404)

    def test_noindex_tag_added(self):
        noindex_string = """<meta name="robots" content="noindex">"""
        PersonPostWithPartyFactory(
            person=self.person, election=ElectionFactory()
        )
        response = self.client.get(self.person_url, follow=True)
        self.assertNotContains(response, noindex_string)
        self.person.delisted = True
        self.person.save()
        response = self.client.get(self.person_url, follow=True)
        self.assertInHTML(noindex_string, response.content.decode("utf8"))

    @freeze_time("2024-07-04")
    def test_deselected(self):
        future_election = ElectionWithPostFactory(
            name="UK Parliamentary general election",
            current=True,
            election_date="2024-07-04",
            slug="parl.cardiff-south-and-penarth.2024-07-04",
        )
        person_post = PersonPostWithPartyFactory(
            person=self.person,
            election=future_election,
            deselected=True,
            deselected_source="www.candidate-party-page.co.uk",
        )

        call_command("import_national_parties")

        response = self.client.get(self.person_url, follow=True)
        self.assertContains(
            response,
            "This candidate has been deselected by their party, but their original party description will remain on the ballot paper.",
        )
        self.assertContains(response, "www.candidate-party-page.co.uk")

        response = self.client.get(
            person_post.post_election.get_absolute_url(), follow=True
        )
        self.assertContains(
            response,
            "This candidate has been deselected by their party, but their original party description will remain on the ballot paper.",
        )
        self.assertContains(response, "www.candidate-party-page.co.uk")
        self.assertNotContains(response, "Party manifesto")


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
