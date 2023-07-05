from django.test import TestCase
from unittest.mock import patch
from datetime import datetime, timedelta

from parties.models import Party


class TestParty(TestCase):
    def test_is_independent(self):
        independent = Party(party_id="ynmp-party:2")
        other = Party(party_id="an:other")

        assert independent.is_independent is True
        assert other.is_independent is False

    def test_get_joint_party_sub_parties(self):
        joint_party = Party(party_id="joint-party:1-2")
        first_sub_party = Party(party_id="party:1", party_name="first_sub")
        first_sub_party.save()
        second_sub_party = Party(party_id="party:2", party_name="second_sub")
        second_sub_party.save()

        sub_parties = joint_party.get_joint_party_sub_parties

        assert len(sub_parties) == 2
        assert sub_parties[0].party_name == "first_sub"
        assert sub_parties[1].party_name == "second_sub"

    def test_is_deregistered(self):
        dereg_party_with_past_date = Party(
            party_id="party:1",
            party_name="Dereg Party",
            date_deregistered=datetime.now().date() - timedelta(days=1),
            status="Deregistered",
        )
        assert dereg_party_with_past_date.is_deregistered

        dereg_party_with_future_date = Party(
            party_id="party:1",
            party_name="Dereg Party",
            date_deregistered=datetime.now().date() + timedelta(days=1),
            status="Deregistered",
        )
        assert dereg_party_with_future_date.is_deregistered is False

        dereg_party_without_date = Party(
            party_id="party:1", party_name="Dereg Party", status="Deregistered"
        )
        assert dereg_party_without_date.is_deregistered is False

    def test_format_name(self):
        dereg_party = Party(
            party_id="party:1",
            party_name="Dereg Party",
            date_deregistered=datetime.now().date() - timedelta(days=1),
        )
        reg_party = Party(party_id="party:2", party_name="Reg Party")
        assert dereg_party.format_name == "Dereg Party (Deregistered)"
        assert reg_party.format_name == "Reg Party"

    @patch("parties.models.get_language")
    def test_get_party_register_url(self, mock):
        independent = Party(party_id="ynmp-party:2", ec_id="ynmp-party:2")
        assert independent.get_party_register_url is None

        party = Party(party_id="ynmp-party:53", ec_id="PP53")
        assert (
            party.get_party_register_url
            == "https://search.electoralcommission.org.uk/English/Registrations/PP53"
        )

        mock.return_value = "cy"
        assert (
            party.get_party_register_url
            == "https://search.electoralcommission.org.uk/Cymraeg/Registrations/PP53"
        )

    def test_format_register(self):
        gb_party = Party(register="GB")
        assert gb_party.format_register == "Great Britain"

        ni_party = Party(register="NI")
        assert ni_party.format_register == "Northern Ireland"

        no_register_party = Party()
        assert no_register_party.format_register is None
