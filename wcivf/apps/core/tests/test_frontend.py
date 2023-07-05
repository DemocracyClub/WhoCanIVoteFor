"""
Tests for the HTML of the site.

Used for making sure meta tags and important information is actually
shown before and after template changes.
"""

from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from dc_utils.tests.helpers import validate_html_str
from people.tests.factories import (
    PersonFactory,
    PersonPostWithPartyFactory,
)
from parties.tests.factories import PartyFactory
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
)

import vcr
import pytest


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
            reverse(
                "email_person_view",
                kwargs={"pk": PersonFactory().pk, "ignored_slug": "sadiq-khan"},
            ),
            reverse("parties_view"),
            PartyFactory().get_absolute_url(),
            reverse("elections_view"),
            ElectionFactory().get_absolute_url(),
            PostElectionFactory().get_absolute_url(),
            reverse("postcode_view", kwargs={"postcode": "E3 2NX"}),
            reverse("api:api-root"),
            reverse("dc_signup_form:mailing_list_signup_view"),
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


class TestBaseTemplate(TestCase):
    def test_base_template(self):
        with self.assertTemplateUsed("dc_base.html"):
            req = self.client.get("/")
            assert req.status_code == 200
            assert "dc_base_naked.html" in (t.name for t in req.templates)
