import pytest

from elections.models import PostElection
from people.management.commands.import_people import Command
from people.models import Person


class TestUpdateCandidacies:
    @pytest.fixture
    def person_data(self):
        return {
            "candidacies": [
                {
                    "elected": False,
                    "party_list_position": 1,
                    "party": {
                        "url": "http://candidates.democracyclub.org.uk/api/next/parties/PP53/",
                        "ec_id": "PP53",
                        "name": "Labour Party",
                        "legacy_slug": "party:53",
                    },
                    "ballot": {
                        "url": "http://candidates.democracyclub.org.uk/api/next/ballots/parl.romsey-and-southampton-north.2010-05-06/",
                        "ballot_paper_id": "parl.romsey-and-southampton-north.2010-05-06",
                    },
                },
            ],
        }

    def test_update_candidacies(self, person_data, mocker):
        person_obj = mocker.MagicMock(spec=Person)
        person_obj.personpost_set.update_or_create.return_value = (False, {})
        ballot = mocker.MagicMock(
            spec=PostElection,
            ballot_paper_id="parl.romsey-and-southampton-north.2010-05-06",
        )
        mocker.patch.object(PostElection.objects, "get", return_value=ballot)

        command = Command()
        command.update_candidacies(
            person_data=person_data,
            person_obj=person_obj,
        )

        person_obj.personpost_set.update_or_create.assert_called_once_with(
            post_election=ballot,
            post=ballot.post,
            election=ballot.election,
            defaults={
                "party_id": "party:53",
                "list_position": 1,
                "elected": False,
            },
        )

    def test_delete_old_candidacies(self, person_data, mocker):
        person_obj = mocker.MagicMock(spec=Person)
        delete = mocker.MagicMock(return_value=(False, {}))
        person_obj.personpost_set.exclude.return_value.delete = delete

        command = Command()
        command.delete_old_candidacies(
            person_data=person_data, person_obj=person_obj
        )

        person_obj.personpost_set.exclude.assert_called_once_with(
            post_election__ballot_paper_id__in=[
                "parl.romsey-and-southampton-north.2010-05-06"
            ]
        )
        delete.assert_called_once()
