from django.test import TestCase

from parties.models import Party


class TestParty(TestCase):
    def test_is_independent(self):
        independent = Party(party_id="ynmp-party:2")
        other = Party(party_id="an:other")

        assert independent.is_independent is True
        assert other.is_independent is False
