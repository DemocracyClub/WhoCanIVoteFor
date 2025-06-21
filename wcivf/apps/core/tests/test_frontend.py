"""
Tests for the HTML of the site.

Used for making sure meta tags and important information is actually
shown before and after template changes.
"""

from datetime import timedelta

import pytest
import vcr
from dateutil.utils import today
from dc_utils.tests.helpers import validate_html_str
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
)
from parties.tests.factories import PartyFactory
from people.tests.factories import (
    PersonPostWithPartyFactory,
)


@override_settings(
    STATICFILES_STORAGE="pipeline.storage.NonPackagingPipelineStorage",
    PIPELINE_ENABLED=False,
)
class TestMetaTags(TestCase):
    important_urls = {
        "homepage": reverse("home_view"),
        "postcode": reverse("postcode_view", kwargs={"postcode": "EC1A 4EU"}),
    }

    @vcr.use_cassette("fixtures/vcr_cassettes/test_postcode_view.yaml")
    def test_200_on_important_urls(self):
        for name, url in self.important_urls.items():
            req = self.client.get(url)
            assert req.status_code == 200


class TestHtml:
    @pytest.fixture
    def urls(self):
        return [
            reverse("home_view"),
            reverse("about_view"),
            reverse("standing_as_a_candidate"),
            reverse("opensearch"),
            reverse("status_check_view"),
            PersonPostWithPartyFactory(
                election=ElectionFactory()
            ).person.get_absolute_url(),
            reverse("parties_view"),
            PartyFactory().get_absolute_url(),
            reverse("elections_view"),
            ElectionFactory().get_absolute_url(),
            PostElectionFactory().get_absolute_url(),
            reverse("postcode_view", kwargs={"postcode": "E3 2NX"}),
            reverse("api:api-root"),
            reverse("feedback_form_view"),
            reverse("sv_voting_system_view"),
            reverse("fptp_voting_system_view"),
            reverse("ams_voting_system_view"),
            reverse("stv_voting_system_view"),
        ]

    @vcr.use_cassette("fixtures/vcr_cassettes/test_mayor_elections.yaml")
    @pytest.mark.django_db
    def test_html_valid(self, client, subtests, urls):
        for url in urls:
            with subtests.test(msg=url):
                resp = client.get(url)
                assert resp.status_code == 200
                _, errors = validate_html_str(resp.content)
                assert errors == ""

    def test_redirects(self, client):
        urls = [
            reverse("ppc_2024:home"),
            reverse("ppc_2024:details"),
        ]
        for url in urls:
            resp = client.get(url)
            assert resp.status_code == 302
            assert (
                resp.url
                == "https://whocanivotefor.co.uk/elections/parl.2024-07-04/uk-parliament-elections/"
            )


class TestBaseTemplate(TestCase):
    def test_base_template(self):
        with self.assertTemplateUsed("dc_base.html"):
            req = self.client.get("/")
            assert req.status_code == 200
            assert "dc_base_naked.html" in (t.name for t in req.templates)


@override_settings(SHOW_UPCOMING_ELECTIONS=True)
class TestHomePageView(TestCase):
    def test_home_page_smoke_test(self):
        req = self.client.get("/")
        self.assertEqual(req.status_code, 200)

    def test_upcoming_elections(self):
        """
        Ensure that ballots replacing another ballot are included in the
        upcoming elections list alongside by-elections.


        These elections are useful to show outside scheduled elections, but
        aren't by-elections.

        """

        election_with_by_election = ElectionFactory(
            election_date=today(), current=True, any_non_by_elections=False
        )
        PostElectionFactory.create(
            election=election_with_by_election,
            ballot_paper_id="local.foo.bar.by.date",
        )

        old_election = ElectionFactory(
            election_date=today() - timedelta(weeks=6),
            current=False,
            slug="local.baz.old_date",
        )

        election_with_replaced = ElectionFactory(
            election_date=today(), current=True, slug="local.baz.date"
        )

        replaced_ballot = PostElectionFactory(
            election=election_with_replaced,
            ballot_paper_id="local.baz.replaced.date",
            cancelled=False,
        )
        replaced_ballot.save()
        PostElectionFactory(
            election=old_election,
            ballot_paper_id="local.baz.bar.old_date",
            cancelled=True,
            replaced_by=replaced_ballot,
        ).save()

        req = self.client.get("/")
        self.assertContains(req, "local.foo.bar.by.date")
        self.assertContains(req, "local.baz.replaced.date")
        self.assertContains(req, "Upcoming Elections")

    def test_ref_in_upcoming_elections(self):
        """
        Ensure that referendums show up in the home page list


        """
        referendum_election = ElectionFactory(
            election_date=today(),
            current=True,
            # This will get marked as True by the importer
            any_non_by_elections=True,
            slug="ref.date",
        )
        PostElectionFactory.create(
            election=referendum_election,
            ballot_paper_id="ref.foo.date",
        )
        req = self.client.get("/")
        self.assertContains(req, "ref.foo.date")
