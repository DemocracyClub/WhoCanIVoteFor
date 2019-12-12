from django.test import TestCase

from elections.helpers import expected_sopn_publish_date
from datetime import date


class ExpectedSoPNDate(TestCase):
    def test_with_territory_code_eng(self):
        expected = expected_sopn_publish_date("local.2019-05-02", "ENG")

        assert expected == date(2019, 4, 4)

    def test_with_territory_code_nir(self):
        expected = expected_sopn_publish_date("local.2019-05-02", "NIR")

        assert expected == date(2019, 4, 8)

    def test_with_territory_code_unknown(self):
        expected = expected_sopn_publish_date("local.2019-05-02", "-")

        assert expected is None

    def test_with_territory_code_unambiguous_election_type(self):
        expected = expected_sopn_publish_date(
            "nia.belfast-east.2017-03-02", "NIR"
        )

        assert expected == date(2017, 2, 8)

    def test_with_territory_code_malformed_id(self):
        expected = expected_sopn_publish_date("whoknows", "ENG")

        assert expected is None
