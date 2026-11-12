import pytest
from core.context_processors import referer_postcode
from django.test import RequestFactory


class TestRefererPostcode:
    @pytest.mark.parametrize(
        "referer_path,expected",
        [
            (
                "WC1E6BT",  # max length postcode, no space
                "WC1E 6BT",
            ),
            (
                "WC1E%206BT",  # max length postcode, with space
                "WC1E 6BT",
            ),
            (
                "WC1E%206BT/123456789012",  # postcode followed by uprn
                "WC1E 6BT",
            ),
        ],
    )
    def test_valid_referers(self, referer_path, expected):
        url = "/mock_destination/"
        http_referer = f"http://testserver/elections/{referer_path}/"
        request = RequestFactory().get(url, HTTP_REFERER=http_referer)
        result = referer_postcode(request)

        assert "referer_postcode" in result
        assert result["referer_postcode"] == expected

    @pytest.mark.parametrize(
        "referer_path",
        [
            "not-elections",  # invalid path
            "elections/QU1 1ZD",  # invalid postcode
            "elections/notapostcode",  # not a postcode
        ],
    )
    def test_invalid_referers(self, referer_path):
        url = "/mock_destination/"
        http_referer = f"http://testserver/{referer_path}/"
        request = RequestFactory().get(url, HTTP_REFERER=http_referer)
        result = referer_postcode(request)
        assert result == {}

    def test_no_referer(self):
        url = "/mock_destination/"
        request = RequestFactory().get(url)
        result = referer_postcode(request)
        assert result == {}
