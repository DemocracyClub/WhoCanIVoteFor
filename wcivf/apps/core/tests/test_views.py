from django.test import TestCase
from django.shortcuts import reverse


class TestPostcodeFormView(TestCase):
    def test_no_postcode(self):
        """
        When postcode is not present in query string no redirect occurs.
        """
        response = self.client.get("/?postcode=")
        assert response.status_code == 200

    def test_has_postcode(self):
        """
        When poscode is present in request GET redirect to the postcode view
        occurs.
        """
        response = self.client.get("/?postcode=TE11ST")

        assert response.status_code == 302
        assert response.url == reverse(
            "postcode_view", kwargs={"postcode": "TE11ST"}
        )

    def test_has_invalid_postcode(self):
        """
        When invalid_postcode is in the request GET redirect does not occur.
        """
        response = self.client.get("/?postcode=TE11ST&invalid_postcode=1")

        assert response.status_code == 200
