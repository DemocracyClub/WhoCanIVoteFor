import pytest
from elections.models import PostElection

from referendums.importers import ReferendumImporter
from referendums.models import Referendum


class TestReferendumImporter:
    @pytest.fixture
    def importer(self):
        url = "https://example.com"
        importer = ReferendumImporter(url=url)
        return importer

    def test_init(self, importer):
        assert importer.url == "https://example.com"

    def test_get_ballots_by_ballot_paper_id(self, importer, mocker):
        filter = mocker.MagicMock(return_value="single_ballot_qs")
        mocker.patch.object(PostElection.objects, "filter", new=filter)
        ballots = importer.get_ballots(
            election_id="local.sheffield.ecclesall.2021-05-06",
        )

        assert ballots == "single_ballot_qs"
        filter.assert_called_once()
        filter.assert_called_once_with(
            ballot_paper_id="local.sheffield.ecclesall.2021-05-06"
        )

    def test_get_ballots_by_election_slug(self, importer, mocker):
        filter = mocker.MagicMock()
        filter.return_value.__bool__.return_value = False
        mocker.patch.object(PostElection.objects, "filter", new=filter)
        importer.get_ballots(
            election_id="local.sheffield.2021-05-06",
        )

        calls = [
            mocker.call(ballot_paper_id="local.sheffield.2021-05-06"),
            mocker.call(election__slug="local.sheffield.2021-05-06"),
        ]
        filter.assert_has_calls(calls, any_order=True)

    def test_create_object_no_question(self, importer, capsys):
        data = {"question": None}
        importer.create_object(data)

        captured = capsys.readouterr()
        assert captured.out == "No question to use, skipping\n"

    def test_create_object_no_ballots(self, importer, mocker, capsys):
        data = {"question": "Yes or no?", "election_id": "bad_id"}
        mocker.patch.object(importer, "get_ballots", return_value=None)
        importer.create_object(data)

        captured = capsys.readouterr()
        assert captured.out == "No ballots so skipping referendum\n"

    def test_create_object_created(self, importer, mocker, capsys):
        data = {"question": "Yes or no?", "election_id": "bad_id"}
        mocker.patch.object(importer, "get_ballots", return_value=["Ballot"])
        referendum = mocker.Mock(pk=1)
        mocker.patch.object(
            Referendum.objects, "create", return_value=referendum
        )

        result = importer.create_object(data)
        captured = capsys.readouterr()

        assert result == referendum
        referendum.ballot_dict.set.assert_called_once_with(["Ballot"])
        assert captured.out == "Created Referendum 1\n"
