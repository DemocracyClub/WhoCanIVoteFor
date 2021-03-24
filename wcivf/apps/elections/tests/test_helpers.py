import pytest
import sys

from django.test import TestCase
from elections.tests.factories import (
    PostFactory,
    ElectionFactory,
)
from elections.helpers import (
    get_election_timetable,
    EEHelper,
    JsonPaginator,
)
from elections.import_helpers import YNRBallotImporter, YNRPostImporter
from elections.models import Election, PostElection, Post
from datetime import date
from elections.tests.factories import PostElectionFactory


class GetElectionTimetable(TestCase):
    def test_with_territory_code_eng(self):
        expected = get_election_timetable("local.2019-05-02", "ENG")

        assert expected == date(2019, 4, 4)

    def test_with_territory_code_nir(self):
        expected = get_election_timetable("local.2019-05-02", "NIR")

        assert expected == date(2019, 4, 8)

    def test_with_territory_code_unknown(self):
        expected = get_election_timetable("local.2019-05-02", "-")

        assert expected is None

    def test_with_territory_code_unambiguous_election_type(self):
        expected = get_election_timetable("nia.belfast-east.2017-03-02", "NIR")

        assert expected == date(2017, 2, 8)

    def test_with_territory_code_malformed_id(self):
        expected = get_election_timetable("whoknows", "ENG")

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

        election_filter.assert_called_once_with(slug__in=["foo_id", "bar_id"])
        election_filter.return_value.delete.assert_called_once()
        postelection_filter.assert_called_once_with(
            ballot_paper_id__in=["foo_id", "bar_id"]
        )
        postelection_filter.return_value.delete.assert_called_once()


class TestYNRBallotImporter(TestCase):
    def setUp(self):
        self.importer = YNRBallotImporter()
        election = ElectionFactory(name="Adur local election")
        self.post = PostFactory(label="Adur local election")
        self.post.elections.add(election)
        self.orphan_post = PostFactory(
            label="Adur local election", ynr_id="foo"
        )

    def test_delete_orphan_posts(self):
        deleted_posts, _ = self.importer.delete_orphan_posts()
        query_set = Post.objects.all()
        self.assertEqual(deleted_posts, 1)
        self.assertEqual(query_set.count(), 1)
        self.assertIn(self.post, query_set)
        self.assertNotIn(self.orphan_post, query_set)


class TestYNRBallotImporterDivisionType:
    @pytest.fixture(autouse=True)
    def mock_ee_helper(self, mocker):
        """
        Mocks the EEHelper get_data method
        """
        mocker.patch.object(EEHelper, "get_data", return_value=None)

    @pytest.fixture
    def ballot(self, mocker):
        """
        Returns an unsaved Ballot object with save method on post mocked
        """
        ballot = PostElectionFactory.build(post__division_type="DIW")
        mocker.patch.object(ballot.post, "save")
        return ballot

    def test_set_division_type_unchanged(self, ballot):
        """
        Test that when division_type is set and not a force update, nothing
        happens
        """
        importer = YNRBallotImporter(force_update=False)

        assert importer.set_division_type(ballot=ballot) is None
        assert ballot.post.division_type == "DIW"
        EEHelper.get_data.assert_not_called()
        ballot.post.save.assert_not_called()

    def test_set_division_type_force_no_ee_data(self, ballot):
        """
        Test that force_update ensures update attempt tries, but doesnt change
        when no data
        """
        importer = YNRBallotImporter(force_update=True)

        assert importer.set_division_type(ballot=ballot) is None
        assert ballot.post.division_type == "DIW"
        EEHelper.get_data.assert_called_once_with(ballot.ballot_paper_id)
        ballot.post.save.assert_not_called()

    def test_set_division_type_changed(self, ballot, mocker):
        """
        Test that division_type gets updated
        """
        importer = YNRBallotImporter(force_update=True)
        division = {"division": {"division_type": "NEW"}}
        mocker.patch.object(EEHelper, "get_data", return_value=division)
        mocker.patch.object(ballot.post, "full_clean")

        assert importer.set_division_type(ballot=ballot) is None
        assert ballot.post.division_type == "NEW"
        EEHelper.get_data.assert_called_once_with(ballot.ballot_paper_id)
        ballot.post.full_clean.assert_called_once()
        ballot.post.save.assert_called_once()


class TestYNRPostImporter:
    def test_update_or_create_from_ballot_dict_uses_id(self, mocker):
        ballot_dict = {
            "post": {
                "id": "foo",
                "slug": "bar",
                "label": "example",
            }
        }
        mock = mocker.Mock(return_value=(1, True))
        mocker.patch("elections.models.Post.objects.update_or_create", mock)
        importer = YNRPostImporter()
        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict)

        mock.assert_called_once_with(
            ynr_id="foo", defaults={"label": "example"}
        )

    def test_update_or_create_from_ballot_dict_uses_slug(self, mocker):
        ballot_dict = {
            "post": {
                "id": None,
                "slug": "bar",
                "label": "example",
            }
        }
        mock = mocker.Mock(return_value=(1, True))
        mocker.patch("elections.models.Post.objects.update_or_create", mock)
        importer = YNRPostImporter()
        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict)

        mock.assert_called_once_with(
            ynr_id="bar", defaults={"label": "example"}
        )
