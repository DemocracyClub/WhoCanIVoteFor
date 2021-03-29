import sys
import pytest
from elections.models import Election, PostElection

from parties.importers import LocalPartyImporter, LocalElection
from parties.models import LocalParty


class TestLocalPartyImporter:
    @pytest.fixture
    def local_election(self):
        return LocalElection(
            date="2021-05-06",
            csv_files=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vQx49JTec8i5oz_x6SJanvSKPc8BccanIlnGR4j0plbD99QFslXw7JEvWSNtdrJiePBMBi0AXkvw3e7/pub?gid=1210343217&single=true&output=csv",
            ],
        )

    @pytest.fixture
    def importer(self, local_election):
        return LocalPartyImporter(election=local_election)

    @pytest.fixture
    def row(self):
        return {
            "Local party name": "Labour Ecclesall",
            "party_id": "53",
            "election_id": "local.sheffield.2021-05-06",
            "Twitter": "https://twitter.com/example",
            "Facebook": "https://facebook.com/example",
            "Website": "https://example.com",
            "Email": "email@example.com",
            "Manifesto Website URL": "http://example.com/manifesto",
            "Manifesto PDF URL": "http://example.com/manifesto.pdf",
        }

    def test_init(self, local_election):
        importer = LocalPartyImporter(election=local_election)
        assert importer.election == local_election
        assert importer.force_update is False
        assert importer.read_from == importer.read_from_url

    def test_init_from_file(self, mocker):
        election = mocker.Mock()
        importer = LocalPartyImporter(election=election, from_file=True)
        assert importer.election == election
        assert importer.force_update is False
        assert importer.read_from == importer.read_from_file

    def test_write(self, importer, mocker):
        mocker.patch.object(sys.stdout, "write")
        importer.write("Foo")
        sys.stdout.write.assert_called_once_with("Foo\n")

    def test_delete_parties_for_election_date(self, importer, mocker):
        filter = mocker.MagicMock()
        filter.return_value.delete.return_value = (0, {})
        mocker.patch.object(LocalParty.objects, "filter", new=filter)
        importer.delete_parties_for_election_date()
        filter.assert_called_once_with(
            post_election__election__election_date=importer.election.date
        )
        filter.return_value.delete.assert_called_once()

    def test_current_elections(self, importer):
        importer.force_update = True
        assert importer.current_elections() is True

    @pytest.mark.parametrize("exists", [True, False])
    def test_current_elections_dont_force(self, importer, mocker, exists):
        filter = mocker.MagicMock()
        filter.return_value.exists.return_value = exists
        mocker.patch.object(Election.objects, "filter", new=filter)
        assert importer.current_elections() is exists
        filter.assert_called_once_with(
            current=True, election_date=importer.election.date
        )
        filter.return_value.exists.assert_called_once()

    def test_get_ballots_filters_by_ballot_paper_id(self, importer, mocker):
        mocker.patch.object(PostElection.objects, "filter", return_value=True)
        parties = mocker.MagicMock()
        result = importer.get_ballots(election_id="Foo", parties=parties)
        assert result is True
        PostElection.objects.filter.assert_called_once()
        PostElection.objects.filter.assert_called_once_with(
            ballot_paper_id="Foo"
        )

    def test_get_ballots_filter_by_election_slug(self, importer, mocker):
        mock = mocker.MagicMock()
        mock.__bool__.return_value = False
        mocker.patch.object(PostElection.objects, "filter", return_value=mock)
        parties = mocker.MagicMock()
        importer.get_ballots(election_id="Foo", parties=parties)
        PostElection.objects.filter.assert_called_with(
            election__slug="Foo",
        )
        mock.exclude.assert_called_once_with(
            localparty__parent__in=parties,
        )

    def test_import_parties_no_current_elections(self, importer, mocker):
        mocker.patch.object(importer, "delete_parties_for_election_date")
        mocker.patch.object(importer, "current_elections", return_value=False)
        mocker.patch.object(importer, "all_rows")

        assert importer.import_parties() is None
        importer.delete_parties_for_election_date.assert_called_once()
        importer.current_elections.assert_called_once()
        importer.all_rows.assert_not_called()

    def test_import_parties_runs(self, importer, row, mocker):
        mocker.patch.object(importer, "delete_parties_for_election_date")
        mocker.patch.object(importer, "current_elections")

        party = mocker.MagicMock()
        mocker.patch.object(importer, "get_parties", return_value=[party])

        ballots = mocker.MagicMock()
        mocker.patch.object(importer, "get_ballots", return_value=ballots)

        mocker.patch.object(importer, "all_rows", return_value=[row])

        mocker.patch.object(importer, "add_local_party")
        mocker.patch.object(importer, "add_manifesto")

        # actual call to do the import
        importer.import_parties()

        # assert what we expet to have been called was called
        importer.delete_parties_for_election_date.assert_called_once()
        importer.current_elections.assert_called_once()
        importer.all_rows.assert_called()
        importer.add_local_party.assert_called_once_with(row, party, ballots)
        importer.add_manifesto.assert_called_once_with(
            row, party, ballots[0].election
        )

    def test_add_local_party(self, importer, row, mocker):
        party = mocker.MagicMock(name="Example Local Party")
        mocker.patch.object(
            LocalParty.objects,
            "update_or_create",
            return_value=(party, True),
        )
        mocker.patch.object(importer, "get_country", return_value="Local")
        party = mocker.MagicMock()
        post_election = mocker.MagicMock()
        ballots = mocker.MagicMock()
        ballots.__iter__.return_value = [post_election]

        importer.add_local_party(row=row, party=party, ballots=ballots)
        LocalParty.objects.update_or_create.assert_called_once_with(
            parent=party,
            post_election=post_election,
            defaults={
                "name": row["Local party name"],
                "twitter": "example",
                "facebook_page": row["Facebook"],
                "homepage": row["Website"],
                "email": row["Email"],
                "is_local": True,
            },
        )

    def test_get_name(self, importer, subtests):
        cases = [
            ({"Local party name": "Welsh Labour"}, "Welsh Labour"),
            ({"Party name": "Welsh Labour"}, "Welsh Labour"),
            ({}, None),
        ]
        for case in cases:
            row = case[0]
            expected = case[1]
            with subtests.test(msg=row):
                result = importer.get_name(row)
                assert result == expected

    def test_test_get_country(self, importer, subtests):
        cases = [
            ("local", "Local"),
            ("senedd", "Wales"),
            ("sp", "Scotland"),
            ("pcc", "UK"),
            ("mayor", "UK"),
            ("another", "UK"),
        ]
        for case in cases:
            election_slug = case[0]
            expected = case[1]
            with subtests.test(msg=case[0]):
                assert importer.get_country(election_slug) == expected
