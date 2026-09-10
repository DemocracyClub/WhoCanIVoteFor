import zoneinfo
from datetime import datetime

import pytest
from leaflets.management.commands.import_leaflets import Command
from leaflets.models import Leaflet
from people.tests.factories import PersonFactory


def make_leaflet_data(
    pk,
    person_id,
    thumb_url="https://example.com/thumb.png",
    date_uploaded="2020-01-01T00:00:00Z",
):
    return {
        "pk": pk,
        "people": [{str(person_id): "Some Person Name"}],
        "first_page_thumb": thumb_url,
        "date_uploaded": date_uploaded,
    }


def make_response(mocker, results, next_url=None):
    response = mocker.Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": results, "next": next_url}
    return response


class TestImportLeafletsCommand:
    @pytest.mark.parametrize(
        "date_str,expected_dt",
        [
            (
                "2025-10-21T08:41:34.886868+01:00",
                datetime(
                    2025,
                    10,
                    21,
                    7,
                    41,
                    34,
                    886868,
                    tzinfo=zoneinfo.ZoneInfo(key="UTC"),
                ),
            ),
            (
                "2015-01-15T08:17:48Z",
                datetime(
                    2015, 1, 15, 8, 17, 48, tzinfo=zoneinfo.ZoneInfo(key="UTC")
                ),
            ),
            (
                "2015-01-15T08:17:48",
                datetime(
                    2015, 1, 15, 8, 17, 48, tzinfo=zoneinfo.ZoneInfo(key="UTC")
                ),
            ),
        ],
        ids=["with_offset", "utc_zulu", "naive"],
    )
    def test_parse_date_uploaded(self, date_str, expected_dt):
        command = Command()
        result = command.parse_date_uploaded(date_str)
        assert result == expected_dt


class TestImportLeafletsCommandHandle:
    @pytest.mark.django_db
    def test_expected_records_imported(self, mocker):
        person_one = PersonFactory()
        person_two = PersonFactory()
        results = [
            make_leaflet_data(
                pk=1,
                person_id=person_one.pk,
                thumb_url="https://example.com/one.png",
                date_uploaded="2020-01-01T00:00:00Z",
            ),
            make_leaflet_data(
                pk=2,
                person_id=person_two.pk,
                thumb_url="https://example.com/two.png",
                date_uploaded="2020-02-02T00:00:00Z",
            ),
        ]
        mocker.patch(
            "leaflets.management.commands.import_leaflets.requests.get",
            return_value=make_response(mocker, results),
        )

        Command().handle()

        assert Leaflet.objects.count() == 2
        leaflet_one = Leaflet.objects.get(leaflet_id=1)
        assert leaflet_one.person == person_one
        assert leaflet_one.thumb_url == "https://example.com/one.png"
        leaflet_two = Leaflet.objects.get(leaflet_id=2)
        assert leaflet_two.person == person_two
        assert leaflet_two.thumb_url == "https://example.com/two.png"

    @pytest.mark.django_db
    def test_pagination_follows_next_url(self, mocker):
        person_one = PersonFactory()
        person_two = PersonFactory()
        page_one = make_response(
            mocker,
            [make_leaflet_data(pk=1, person_id=person_one.pk)],
            next_url="https://electionleaflets.org/api/leaflets/?current=true&page=2",
        )
        page_two = make_response(
            mocker,
            [make_leaflet_data(pk=2, person_id=person_two.pk)],
            next_url=None,
        )
        mocked_get = mocker.patch(
            "leaflets.management.commands.import_leaflets.requests.get",
            side_effect=[page_one, page_two],
        )

        Command().handle()

        assert mocked_get.call_count == 2
        mocked_get.assert_any_call(
            "https://electionleaflets.org/api/leaflets/?current=true"
        )
        mocked_get.assert_any_call(
            "https://electionleaflets.org/api/leaflets/?current=true&page=2"
        )
        assert Leaflet.objects.count() == 2
        assert Leaflet.objects.filter(leaflet_id=1).exists()
        assert Leaflet.objects.filter(leaflet_id=2).exists()

    @pytest.mark.django_db
    def test_existing_leaflets_cleared_before_import(self, mocker):
        old_person = PersonFactory()
        Leaflet.objects.create(
            person=old_person,
            leaflet_id=999,
            thumb_url="https://example.com/old.png",
        )
        new_person = PersonFactory()
        results = [make_leaflet_data(pk=1, person_id=new_person.pk)]
        mocker.patch(
            "leaflets.management.commands.import_leaflets.requests.get",
            return_value=make_response(mocker, results),
        )

        Command().handle()

        assert not Leaflet.objects.filter(leaflet_id=999).exists()
        assert Leaflet.objects.count() == 1
        assert Leaflet.objects.filter(leaflet_id=1).exists()

    @pytest.mark.django_db
    def test_transaction_rolled_back_on_exception(self, mocker):
        old_person = PersonFactory()
        Leaflet.objects.create(
            person=old_person,
            leaflet_id=999,
            thumb_url="https://example.com/old.png",
        )
        new_person = PersonFactory()
        page_one = make_response(
            mocker,
            [make_leaflet_data(pk=1, person_id=new_person.pk)],
            next_url="https://electionleaflets.org/api/leaflets/?current=true&page=2",
        )
        mocker.patch(
            "leaflets.management.commands.import_leaflets.requests.get",
            side_effect=[page_one, ConnectionError("boom")],
        )

        with pytest.raises(ConnectionError):
            Command().handle()

        # Original leaflet still present and new leaflet not persisted
        assert Leaflet.objects.filter(leaflet_id=999).exists()
        assert not Leaflet.objects.filter(leaflet_id=1).exists()
        assert Leaflet.objects.count() == 1
