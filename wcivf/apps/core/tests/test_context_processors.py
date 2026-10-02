import pytest
from core.context_processors import referer_postcode
from django.test import RequestFactory


class TestRefererPostcode:
    @pytest.mark.parametrize(
        "postcode,expected",
        [
            (
                "WC1E6BT",  # max length postcode, no space
                "WC1E 6BT",
            ),
            (
                "WC1E%206BT",  # max length postcode, with space
                "WC1E 6BT",
            ),
        ],
    )
    def test_valid_referer(self, postcode, expected):
        url = "/mock_destination/"
        http_referer = f"http://testserver/elections/{postcode}/"
        request = RequestFactory().get(url, HTTP_REFERER=http_referer)
        result = referer_postcode(request)

        assert result["referer_postcode"] == expected

    def test_invalid_referer(self):
        url = "/mock_destination/"
        http_referer = "http://testserver/not-elections/"
        request = RequestFactory().get(url, HTTP_REFERER=http_referer)
        result = referer_postcode(request)
        assert result == {}
