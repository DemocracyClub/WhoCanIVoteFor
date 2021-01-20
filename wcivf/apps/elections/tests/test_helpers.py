import pytest
import sys

from django.test import TestCase

from elections.helpers import (
    expected_sopn_publish_date,
    EEHelper,
    JsonPaginator,
)
from elections.models import Election, PostElection
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


class TestEEHelper:
    @pytest.fixture
    def ee_helper(self, settings):
        settings.EE_BASE = "https://elections.democracyclub.org.uk"
        return EEHelper()

    def test_base_elections_url(self, ee_helper):
        assert (
            ee_helper.base_elections_url
            == "https://elections.democracyclub.org.uk/api/elections/"
        )

    @pytest.mark.freeze_time("2021-02-20")
    def test_deleted_election_ids(self, ee_helper, mocker):
        """
        Check a generator object of ID's to be deleted is returned.
        Patchs the JsonPaginator so that no actual API call is made, and
        instead return mock data to match the structure of the API
        """
        mock_data = [
            {"results": [{"election_id": "foo_id"}, {"election_id": "bar_id"}]},
        ]
        paginator = mocker.MagicMock(spec=JsonPaginator)
        paginator.return_value.__iter__.return_value = iter(mock_data)
        mocker.patch("elections.helpers.JsonPaginator", new=paginator)

        result = ee_helper.deleted_election_ids

        assert result == ["foo_id", "bar_id"]
        paginator.assert_called_once_with(
            page1="https://elections.democracyclub.org.uk/api/elections/?deleted=1&poll_open_date__gte=2021-01-01",
            stdout=sys.stdout,
        )

    @pytest.mark.django_db
    def test_deleted_deleted_elections(self, ee_helper, mocker):
        """
        Patch the EEHelper to return a list of ID's to be deleted
        Patch the filter method on the Election QuerySet
        Assert that the correct kwargs are passed to the filter call
        Assert that delete is called on the return value
        """
        mocker.patch.object(
            EEHelper,
            "deleted_election_ids",
            new_callable=mocker.PropertyMock,
            return_value=["foo_id", "bar_id"],
        )
        election_filter = mocker.MagicMock()
        election_filter.return_value.delete.return_value = ("foo", "bar")
        mocker.patch.object(Election.objects, "filter", new=election_filter)

        postelection_filter = mocker.MagicMock()
        postelection_filter.return_value.delete.return_value = ("foo", "bar")
        mocker.patch.object(
            PostElection.objects, "filter", new=postelection_filter
        )

        ee_helper.delete_deleted_elections()

        election_filter.assert_called_once_with(
            slug__in=["foo_id", "bar_id"], current=False
        )
        election_filter.return_value.delete.assert_called_once()
        postelection_filter.assert_called_once_with(
            ballot_paper_id__in=["foo_id", "bar_id"]
        )
        postelection_filter.return_value.delete.assert_called_once()
