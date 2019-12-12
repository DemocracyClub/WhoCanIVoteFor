"""
Tests for the HTML of the site.

Used for making sure meta tags and important information is actually
shown before and after template changes.
"""


from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

import vcr


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
