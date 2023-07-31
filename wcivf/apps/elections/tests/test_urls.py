from django.shortcuts import reverse
from django.test import TestCase
from django.test.utils import override_settings


@override_settings(USE_I18N=True, LANGUAGE_CODE="cy")
class TestTranslatedURL(TestCase):
    def test_translated_ams_url(self):
        response = self.client.get(reverse("ams_voting_system_view"))
        self.assertContains(response, "<h2>Y System Aelodau Ychwanegol</h2>")

    def test_fptp_page_url(self):
        response = self.client.get(reverse("fptp_voting_system_view"))
        self.assertContains(response, "<h2>Cyntaf i'r felin (FPTP)</h2>")

    def test_translated_sv_url(self):
        response = self.client.get(reverse("sv_voting_system_view"))
        self.assertContains(response, "<h2>Pleidlais Atodol</h2>")

    # TO DO add once we have this template translated
    # def test_translated_stv_url(self):
    #     response = self.client.get(reverse("stv_voting_system_view"))
    #     self.assertContains(response, "<h2></h2>")
