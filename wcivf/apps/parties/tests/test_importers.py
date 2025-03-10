import sys

import pytest
from elections.models import Election, PostElection, PostElectionQuerySet
from parties.importers import (
    LocalElection,
    LocalPartyImporter,
    NationalElection,
    NationalPartyImporter,
)
from parties.models import LocalParty, NationalParty


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
            "X": "https://twitter.com/example",
            "Instagram": "https://www.instagram.com/example",
            "Bluesky": "https://www.bluesky.com/example",
            "Facebook": "https://facebook.com/example",
            "Website": "https://example.com",
            "Email": "email@example.com",
            "Manifesto Website URL": "http://example.com/manifesto",
            "Manifesto PDF URL": "http://example.com/manifesto.pdf",
            "Party broadcast": "",
            "Contact page": "",
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

    def test_delete_parties(self, importer, mocker):
        filter = mocker.MagicMock()
        filter.return_value.delete.return_value = (0, {})
        mocker.patch.object(LocalParty.objects, "filter", new=filter)
        importer.delete_parties()
        filter.assert_called_once_with(file_url__in=importer.election.csv_files)
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
        mock_qs = mocker.MagicMock(spec=PostElectionQuerySet)
        mocker.patch.object(
            PostElection.objects, "filter", return_value=mock_qs
        )
        importer.get_ballots(election_id="Foo", parties=["parties"])
        PostElection.objects.filter.assert_called_once_with(
            ballot_paper_id="Foo",
        )
        mock_qs.filter.assert_called_once_with(
            personpost__party__in=["parties"]
        )

    def test_get_ballots_filter_by_election_slug(self, importer, mocker):
        mock = mocker.MagicMock()
        mock.__bool__.return_value = False
        mocker.patch.object(PostElection.objects, "filter", return_value=mock)
        importer.get_ballots(election_id="Foo", parties=["parties"])
        PostElection.objects.filter.assert_called_with(
            election__slug="Foo",
        )
        mock.exclude.return_value.filter.assert_called_once_with(
            personpost__party__in=["parties"],
        )

    def test_import_parties_no_current_elections(self, importer, mocker):
        mocker.patch.object(importer, "delete_parties")
        mocker.patch.object(importer, "delete_manifestos")
        mocker.patch.object(importer, "current_elections", return_value=False)
        mocker.patch.object(importer, "read_from_url")

        assert importer.import_parties() is None
        importer.delete_parties.assert_called_once()
        importer.delete_manifestos.assert_called_once()
        importer.current_elections.assert_called_once()
        importer.read_from_url.assert_not_called()

    def test_import_parties_runs(self, importer, row, mocker):
        mocker.patch.object(importer, "delete_parties")
        mocker.patch.object(importer, "delete_manifestos")
        mocker.patch.object(importer, "current_elections")

        party = mocker.MagicMock()
        mocker.patch.object(importer, "get_parties", return_value=[party])

        ballots = mocker.MagicMock()
        ballots.values_list.return_value = [1, 2, 3, 4]
        mocker.patch.object(importer, "get_ballots", return_value=ballots)

        mocker.patch.object(importer, "read_from", return_value=[row])

        mocker.patch.object(importer, "add_local_party")
        mocker.patch.object(importer, "add_manifesto")
        mock_elections = mocker.MagicMock()
        mock_elections.distinct.return_value = ["election_obj"]
        mocker.patch.object(
            Election.objects, "filter", return_value=mock_elections
        )

        # actual call to do the import
        importer.import_parties()

        # assert what we expect to have been called was called
        importer.delete_parties.assert_called_once()
        importer.delete_manifestos.assert_called_once()
        importer.current_elections.assert_called_once()
        file_url = importer.election.csv_files[0]
        importer.add_local_party.assert_called_once_with(
            row, party, ballots, file_url
        )

        importer.add_manifesto.assert_called_once_with(
            row, party, "election_obj", file_url
        )
        Election.objects.filter.assert_called_once_with(
            postelection__in=[1, 2, 3, 4]
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
        ballots.filter.return_value.distinct.return_value = [post_election]

        file_url = importer.election.csv_files[0]
        importer.add_local_party(
            row=row, party=party, ballots=ballots, file_url=file_url
        )

        ballots.filter.assert_called_once_with(personpost__party=party)
        LocalParty.objects.update_or_create.assert_called_once_with(
            parent=party,
            post_election=post_election,
            defaults={
                "name": row["Local party name"],
                "twitter": "example",
                "instagram": row["Instagram"],
                "bluesky": row["Bluesky"],
                "facebook_page": row["Facebook"],
                "homepage": row["Website"],
                "email": row["Email"],
                "is_local": True,
                "youtube_profile_url": "",
                "contact_page_url": "",
                "file_url": file_url,
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


class TestNationalPartyImporter:
    @pytest.fixture
    def national_election(self):
        return NationalElection(
            date="2024-07-04",
            csv_files=[
                "https://docs.google.com/spreadsheets/d/e/2PACX-1vS0GJ6wED4d87K1AMXTxxfYl1L-RwjuH-DY1lcwAH9Wj8MChrxPRVDXqc1dzMW8sVdGDLXcBi0usnDl/pub?gid=0&single=true&output=csv"
            ],
        )

    @pytest.fixture
    def importer(self, national_election):
        return NationalPartyImporter(election=national_election)

    @pytest.fixture
    def row(self):
        return {
            "Party Name": "Labour Ecclesall",
            "party_id": "53",
            "election_id": "local.sheffield.2021-05-06",
            "Instagram": "https://instagram.com/example",
            "Facebook": "https://facebook.com/example",
            "Website": "https://example.com",
            "Email": "email@example.com",
            "Party Political Broadcast URL": "http://example.com/ppb",
            "Manifesto Website URL": "http://example.com/manifesto",
            "Manifesto PDF URL": "http://example.com/manifesto.pdf",
        }

    def test_init(self, national_election):
        importer = NationalPartyImporter(election=national_election)
        assert importer.election == national_election
        assert importer.force_update is False
        assert importer.read_from == importer.read_from_url

    def test_init_from_file(self, mocker):
        election = mocker.Mock()
        importer = NationalPartyImporter(election=election, from_file=True)
        assert importer.election == election
        assert importer.force_update is False
        assert importer.read_from == importer.read_from_file

    def test_write(self, importer, mocker):
        mocker.patch.object(sys.stdout, "write")
        importer.write("Foo")
        sys.stdout.write.assert_called_once_with("Foo\n")

    def test_delete_parties(self, importer, mocker):
        filter = mocker.MagicMock()
        filter.return_value.delete.return_value = (0, {})
        mocker.patch.object(NationalParty.objects, "filter", new=filter)
        importer.delete_parties()
        filter.assert_called_once_with(file_url__in=importer.election.csv_files)
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
        mock_qs = mocker.MagicMock(spec=PostElectionQuerySet)
        mocker.patch.object(
            PostElection.objects, "filter", return_value=mock_qs
        )
        importer.get_ballots(election_id="Foo", parties=["parties"])
        PostElection.objects.filter.assert_called_once_with(
            ballot_paper_id="Foo",
        )
        mock_qs.filter.assert_called_once_with(
            personpost__party__in=["parties"]
        )

    def test_get_ballots_filter_by_election_slug(self, importer, mocker):
        mock = mocker.MagicMock()
        mock.__bool__.return_value = False
        mocker.patch.object(PostElection.objects, "filter", return_value=mock)
        importer.get_ballots(election_id="Foo", parties=["parties"])
        PostElection.objects.filter.assert_called_with(
            election__slug="Foo",
        )
        mock.exclude.return_value.filter.assert_called_once_with(
            personpost__party__in=["parties"],
        )

    def test_import_parties_no_current_elections(self, importer, mocker):
        mocker.patch.object(importer, "delete_parties")
        mocker.patch.object(importer, "delete_manifestos")
        mocker.patch.object(importer, "current_elections", return_value=False)
        mocker.patch.object(importer, "read_from_url")

        assert importer.import_parties() is None
        importer.delete_parties.assert_called_once()
        importer.delete_manifestos.assert_called_once()
        importer.current_elections.assert_called_once()
        importer.read_from_url.assert_not_called()

    def test_import_parties_runs(self, importer, row, mocker):
        mocker.patch.object(importer, "delete_parties")
        mocker.patch.object(importer, "delete_manifestos")
        mocker.patch.object(importer, "current_elections")

        party = mocker.MagicMock()
        mocker.patch.object(importer, "get_parties", return_value=[party])

        ballots = mocker.MagicMock()
        ballots.values_list.return_value = [1, 2, 3, 4]
        mocker.patch.object(importer, "get_ballots", return_value=ballots)

        mocker.patch.object(importer, "read_from", return_value=[row])
        mock_elections = mocker.MagicMock()
        mock_elections.distinct.return_value = ["election_obj"]
        mocker.patch.object(importer, "add_national_party")
        mocker.patch.object(importer, "add_manifesto")

        mocker.patch.object(
            Election.objects, "filter", return_value=mock_elections
        )

        # actual call to do the import
        importer.import_parties()

        # assert what we expect to have been called was called
        importer.delete_parties.assert_called_once()
        importer.delete_manifestos.assert_called_once()
        importer.current_elections.assert_called_once()
        file_url = importer.election.csv_files[0]
        importer.add_national_party.assert_called_once_with(
            row, party, ballots, file_url
        )

        importer.add_manifesto.assert_called_once_with(
            row, party, "election_obj", file_url
        )
        Election.objects.filter.assert_called_once_with(
            postelection__in=[1, 2, 3, 4]
        )

    def test_add_national_party(self, importer, row, mocker):
        party = mocker.MagicMock(name="Example National Party")
        mocker.patch.object(
            NationalParty.objects,
            "update_or_create",
            return_value=(party, True),
        )
        party = mocker.MagicMock()
        post_election = mocker.MagicMock()
        ballots = mocker.MagicMock()
        ballots.filter.return_value.distinct.return_value = [post_election]

        file_url = importer.election.csv_files[0]
        importer.add_national_party(
            row=row, party=party, ballots=ballots, file_url=file_url
        )

        ballots.filter.assert_called_once_with(personpost__party=party)
        NationalParty.objects.update_or_create.assert_called_once_with(
            parent=party,
            post_election=post_election,
            defaults={
                "name": row["Party Name"],
                "instagram": row["Instagram"],
                "facebook_page": row["Facebook"],
                "homepage": row["Website"],
                "email": row["Email"],
                "youtube_profile_url": "",
                "contact_page_url": "",
                "party_political_broadcast": "",
                "file_url": file_url,
                "is_national": True,
            },
        )

    def test_get_name(self, importer, subtests):
        cases = [
            ({"National party name": "Welsh Labour"}, "Welsh Labour"),
            ({"Party Name": "Welsh Labour"}, "Welsh Labour"),
            ({}, None),
        ]
        for case in cases:
            row = case[0]
            expected = case[1]
            with subtests.test(msg=row):
                result = importer.get_name(row)
                assert result == expected
