import pytest
from core.helpers import clean_postcode, validate_postcode
from django.forms import ValidationError


class TestCleanPostcode:
    @pytest.mark.parametrize(
        "input,expected",
        [
            (
                "WC1E6BT",  # max length postcode, no space
                "WC1E 6BT",
            ),
            (
                "WC1E 6BT",  # max length postcode, with space
                "WC1E 6BT",
            ),
            (
                "WC1E+6BT",  # postcode with +
                "WC1E 6BT",
            ),
        ],
    )
    def test_clean_postcode(self, input, expected):
        assert clean_postcode(input) == expected


class TestValidatePostcode:
    def test_valid(self):
        assert validate_postcode("WC1E 6BT")

    @pytest.mark.parametrize(
        "input",
        [
            "Not a postcode",  # not a postcode
            "QU1 1ZD",  # invalid postcode
        ],
    )
    def test_invalid(self, input):
        with pytest.raises(ValidationError):
            validate_postcode(input)
