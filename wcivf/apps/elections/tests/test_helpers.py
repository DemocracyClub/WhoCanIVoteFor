import sys
from datetime import date

import pytest
from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from elections.helpers import (
    EEHelper,
    JsonPaginator,
    get_election_timetable,
)
from elections.import_helpers import YNRBallotImporter, YNRPostImporter
from elections.models import Election, Post, PostElection
from elections.tests.factories import (
    ElectionFactory,
    PostElectionFactory,
    PostFactory,
)
from parties.models import Party
from people.models import PersonPost


class GetElectionTimetable(TestCase):
    def test_with_territory_code_eng(self):
        expected = get_election_timetable("local.2019-05-02", "ENG")

        assert expected.poll_date == date(2019, 5, 2)

    def test_with_territory_code_nir(self):
        expected = get_election_timetable("local.2019-05-02", "NIR")

        assert expected.poll_date == date(2019, 5, 2)

    def test_with_territory_code_unknown(self):
        expected = get_election_timetable("local.2019-05-02", "-")

        assert expected is None

    def test_with_territory_code_unambiguous_election_type(self):
        expected = get_election_timetable("nia.belfast-east.2017-03-02", "NIR")

        assert expected.poll_date == date(2017, 3, 2)

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


class TestYNRBallotImporter:
    @pytest.fixture
    def importer(self, mocker):
        importer = YNRBallotImporter()
        mocker.patch.object(importer.ee_helper, "prewarm_cache")
        mocker.patch.object(
            importer, "get_paginator", return_value=[mocker.Mock()]
        )
        mocker.patch.object(importer, "add_ballots")
        mocker.patch.object(importer, "attach_cancelled_ballot_info")
        mocker.patch.object(importer, "delete_orphan_posts")
        return importer

    @pytest.mark.django_db
    def test_delete_orphan_posts(self):
        importer = YNRBallotImporter()
        election = ElectionFactory(name="Adur local election")
        self.post = PostFactory(label="Adur local election")
        self.post.elections.add(election)
        self.orphan_post = PostFactory(
            label="Adur local election", ynr_id="foo"
        )

        deleted_posts, _ = importer.delete_orphan_posts()
        query_set = Post.objects.all()
        assert deleted_posts == 1
        assert query_set.count() == 1
        assert self.post in query_set
        assert self.orphan_post not in query_set

    def test_do_import_no_params(self, importer):
        """
        When no params and not current_only this is a full import the
        ee cache should be used and post ballot tasks should be run
        """
        assert importer.current_only is False
        assert importer.force_metadata is False
        importer.do_import(params=None)
        importer.ee_helper.prewarm_cache.assert_called_once_with(current=True)

        expected_url = (
            f"{settings.YNR_BASE}/media/cached-api/latest/ballots-000001.json"
        )
        importer.get_paginator.assert_called_once_with(expected_url)
        importer.add_ballots.assert_called_once()
        importer.attach_cancelled_ballot_info.assert_called_once()
        importer.delete_orphan_posts.assert_called_once()

    def test_do_import_with_params(self, importer):
        """
        When no params this is a not a full import so the cache should
        not be used and post ballot tasks not run
        """
        assert importer.current_only is False
        importer.do_import(params={"election_date": "2021-05-06"})
        importer.ee_helper.prewarm_cache.assert_not_called()

        expected_url = f"{settings.YNR_BASE}/api/next/ballots/?election_date=2021-05-06&page_size=200"
        importer.get_paginator.assert_called_once_with(expected_url)
        importer.add_ballots.assert_called_once()
        importer.attach_cancelled_ballot_info.assert_not_called()
        importer.delete_orphan_posts.assert_called_once()

    def test_do_import_no_params_current_only(self, importer):
        """
        When no params this is a not a full import so the cache should
        not be used and post ballot tasks not run
        """
        importer.current_only = True
        importer.recently_updated = False
        assert importer.force_metadata is False
        importer.do_import(params=None)
        importer.ee_helper.prewarm_cache.assert_called_once_with(current=True)

        expected_url = (
            f"{settings.YNR_BASE}/api/next/ballots/?current=True&page_size=200"
        )
        importer.get_paginator.assert_called_once_with(expected_url)
        importer.add_ballots.assert_called_once()
        # this gets called when current_only used
        importer.attach_cancelled_ballot_info.assert_called()
        importer.delete_orphan_posts.assert_called_once()

    def test_should_prewarm_ee_cache(self, importer):
        importer.params = {"election_date": "2021-05-06"}
        importer.recently_updated = False
        assert importer.should_prewarm_ee_cache is False
        importer.params = {}
        importer.recently_updated = True
        assert importer.should_prewarm_ee_cache is False
        importer.recently_updated = False
        importer.params = {}
        assert importer.should_prewarm_ee_cache is True

    def test_is_full_import(self, importer):
        importer.params = {"election_date": "2021-05-06"}
        importer.recently_updated = False
        importer.current_only = False
        assert importer.is_full_import is False
        importer.params = {}
        importer.recently_updated = True
        importer.current_only = False
        assert importer.is_full_import is False
        importer.params = {}
        importer.recently_updated = False
        importer.current_only = True
        assert importer.is_full_import is False
        importer.params = {}
        importer.recently_updated = False
        importer.current_only = False
        assert importer.is_full_import is True

    def test_build_params(self, importer, mocker):
        assert importer.build_params(params=None) == {}

        importer.current_only = True
        assert importer.build_params(params=None) == {
            "page_size": 200,
            "current": True,
        }

        importer.current_only = False
        importer.recently_updated = True
        mocker.patch.object(importer, "get_last_updated")
        ts = timezone.now()
        importer.get_last_updated.return_value = ts

        result = importer.build_params(params=None)
        assert result == {"last_updated": ts.isoformat(), "page_size": 200}

        importer.api_key = "test_api_key"
        result = importer.build_params(params={"foo": "bar"})
        assert result == {
            "last_updated": ts.isoformat(),
            "page_size": 200,
            "foo": "bar",
            "auth_token": "test_api_key",
        }

    def test_should_run_post_ballot_import_tasks(
        self, importer, mocker, subtests
    ):
        test_cases = [
            {"full_import": True, "current_only": True, "expected": True},
            {"full_import": False, "current_only": True, "expected": True},
            {"full_import": True, "current_only": False, "expected": True},
            {"full_import": False, "current_only": False, "expected": False},
        ]
        for case in test_cases:
            with subtests.test(msg=str(case)):
                full_import = mocker.PropertyMock(
                    return_value=case["full_import"]
                )
                mocker.patch.object(
                    importer.__class__,
                    "is_full_import",
                    new=full_import,
                )
                importer.current_only = case["current_only"]
                assert (
                    importer.should_run_post_ballot_import_tasks
                    is case["expected"]
                )

    def test_import_url(self, importer, mocker, subtests):
        test_cases = [
            {
                "full_import": True,
                "url": "/media/cached-api/latest/ballots-000001.json",
                "params": None,
            },
            {
                "full_import": False,
                "url": "/api/next/ballots/?foo=bar",
                "params": {"foo": "bar"},
            },
        ]
        for case in test_cases:
            with subtests.test(msg=str(case)):
                full_import = mocker.PropertyMock(
                    return_value=case["full_import"]
                )
                mocker.patch.object(
                    importer.__class__,
                    "is_full_import",
                    new=full_import,
                )
                importer.params = case["params"]
                expected = f"{settings.YNR_BASE}{case['url']}"
                assert importer.import_url == expected

    def test_add_replaced_ballot(self, importer, mocker, subtests):
        ballot = mocker.Mock()
        test_cases = [
            {
                "side_effect": PostElection.DoesNotExist,
                "expected": False,
                "assert": ballot.replaces.add.assert_not_called,
                "replaced_ballot_id": None,
            },
            {
                "side_effect": PostElection.DoesNotExist,
                "expected": False,
                "assert": ballot.replaces.add.assert_not_called,
                "replaced_ballot_id": "not.a.valid.ballot.paper.id",
            },
            {
                "side_effect": None,
                "expected": True,
                "assert": ballot.replaces.add.assert_called_once,
                "replaced_ballot_id": "local.sheffield.fulwood.2020-05-07",
            },
        ]
        for test_case in test_cases:
            with subtests.test(msg=str(test_case)):
                mocker.patch.object(
                    PostElection.objects,
                    "get",
                    side_effect=test_case["side_effect"],
                )
                result = importer.add_replaced_ballot(
                    ballot=ballot,
                    replaced_ballot_id=test_case["replaced_ballot_id"],
                )
                assert result is test_case["expected"]
                test_case["assert"]()


class TestYNRImporterAddBallots:
    @pytest.fixture
    def ballot_dict(self):
        return {
            "ballot_paper_id": "local.sheffield.fulwood.2021-05-06",
            "winner_count": 1,
            "cancelled": False,
            "candidates_locked": False,
            "replaces": "local.sheffield.fulwood.2020-05-07",
            "last_updated": "2021-10-12T00:00:00+00:00",
            "candidacies": [],
            "results": [],
        }

    @pytest.fixture
    def post(self, mocker):
        return mocker.MagicMock(spec=Post)

    @pytest.fixture
    def election(self, mocker):
        return mocker.MagicMock(spec=Election)

    @pytest.fixture
    def ballot(self, mocker):
        ballot = mocker.MagicMock(spec=PostElection)
        ballot.election.current = False
        return ballot

    @pytest.fixture
    def importer(self, post, election, ballot, mocker):
        importer = YNRBallotImporter()
        importer.exclude_candidacies = True
        mocker.patch.object(
            importer.election_importer,
            "update_or_create_from_ballot_dict",
            return_value=election,
        )
        mocker.patch.object(
            importer.post_importer,
            "update_or_create_from_ballot_dict",
            return_value=post,
        )
        mocker.patch.object(importer, "add_replaced_ballot")
        mocker.patch.object(importer, "import_metadata_from_ee")
        mocker.patch.object(
            PostElection.objects,
            "update_or_create",
            return_value=(ballot, False),
        )
        return importer

    @pytest.mark.django_db
    def test_add_ballots_creates_objects(
        self, importer, ballot_dict, post, election
    ):
        """
        Test that the methods to update or create Election and Post
        objects are called, and that a PostElection is updated with
        those objects and data from the the ballot dict
        """
        results = {"results": [ballot_dict]}
        importer.recently_updated = True
        importer.add_ballots(results=results)

        importer.election_importer.update_or_create_from_ballot_dict.assert_called_once_with(
            ballot_dict
        )
        importer.post_importer.update_or_create_from_ballot_dict.assert_called_once_with(
            ballot_dict
        )
        PostElection.objects.update_or_create.assert_called_once_with(
            ballot_paper_id="local.sheffield.fulwood.2021-05-06",
            defaults={
                "election": election,
                "post": post,
                "winner_count": 1,
                "cancelled": False,
                "locked": False,
                "ynr_modified": "2021-10-12T00:00:00+00:00",
            },
        )

    @pytest.mark.django_db
    def test_add_ballots_not_recently_updated(self, importer, ballot_dict):
        """
        Test that when not using recently_updated that the method to
        add the replaced ballot relationship is not called
        """
        results = {"results": [ballot_dict]}
        importer.recently_updated = False
        importer.add_ballots(results=results)

        importer.add_replaced_ballot.assert_not_called()

    @pytest.mark.django_db
    def test_add_ballots_is_recently_updated(
        self,
        importer,
        ballot_dict,
        ballot,
    ):
        """
        Test that when using recently_updated that the method to add
        the replaced ballot relationship is called
        """
        results = {"results": [ballot_dict]}
        importer.recently_updated = True
        importer.add_ballots(results=results)

        importer.add_replaced_ballot.assert_called_once_with(
            ballot=ballot,
            replaced_ballot_id="local.sheffield.fulwood.2020-05-07",
        )

    @pytest.mark.django_db
    def test_import_metadata_from_ee(
        self, importer, ballot_dict, ballot, subtests
    ):
        """
        For each test case, make sure that metadata is or is not
        imported from EE
        """
        results = {"results": [ballot_dict]}

        test_cases = [
            {
                "force_metadata": False,
                "current": False,
                "assert": importer.import_metadata_from_ee.assert_not_called,
            },
            {
                "force_metadata": True,
                "current": False,
                "assert": importer.import_metadata_from_ee.assert_called_once,
            },
            {
                "force_metadata": False,
                "current": True,
                "assert": importer.import_metadata_from_ee.assert_called_once,
            },
            {
                "force_metadata": True,
                "current": True,
                "assert": importer.import_metadata_from_ee.assert_called_once,
            },
        ]
        for test_case in test_cases:
            # clear old calls before each test
            importer.import_metadata_from_ee.reset_mock()
            with subtests.test(msg=str(test_case)):
                ballot.election.current = test_case["current"]
                importer.force_metadata = test_case["force_metadata"]
                importer.add_ballots(results=results)
                test_case["assert"]()

    @pytest.mark.django_db
    def test_import_ballots_adds_candidacies(
        self, mocker, importer, ballot_dict, ballot
    ):
        """
        Tests that if candidacies are included the importer will create them
        """
        ballot_dict["candidacies"] = [
            {
                "person": {"name": "Joe Bloggs", "id": "9876"},
                "result": None,
                "elected": False,
                "deselected": False,
                "deselected_source": None,
                "party_list_position": None,
                "party": {
                    "url": "http://candidates.democracyclub.org.uk/api/next/parties/PP53/",
                    "ec_id": "PP53",
                    "name": "Labour Party",
                    "legacy_slug": "party:53",
                    "created": "2022-02-16T16:23:03.962770Z",
                    "modified": "2022-03-10T10:12:26.510945Z",
                },
                "party_name": "Labour Party",
                "party_description_text": "Labour Party",
                "created": "2022-03-16T11:25:42.328768Z",
                "modified": "2022-03-17T12:36:20.946155Z",
                "ballot": {
                    "url": "http://candidates.democracyclub.org.uk/api/next/ballots/local.cardiff.gabalfa.2022-05-05/",
                    "ballot_paper_id": "local.cardiff.gabalfa.2022-05-05",
                },
                "previous_party_affiliations": [
                    {
                        "url": "http://candidates.democracyclub.org.uk/api/next/parties/ynmp-party:2/",
                        "ec_id": "ynmp-party:2",
                        "name": "Independent",
                        "legacy_slug": "ynmp-party:2",
                        "created": "2022-02-16T15:39:15.647123Z",
                        "modified": "2022-02-16T17:13:11.323855Z",
                    }
                ],
            },
        ]

        results = {"results": [ballot_dict]}
        importer.exclude_candidacies = False
        importer.recently_updated = True

        person_post = mocker.MagicMock(spec=PersonPost)
        mocker.patch.object(
            PersonPost.objects, "create", return_value=person_post
        )
        party = mocker.MagicMock(spec=Party)
        mocker.patch.object(Party.objects, "get", return_value=party)
        importer.add_ballots(results=results)

        ballot.personpost_set.all.return_value.delete.assert_called_once()

        PersonPost.objects.create.assert_called_once()
        Party.objects.get.assert_called_once_with(party_id="ynmp-party:2")
        person_post.previous_party_affiliations.add.assert_called_once_with(
            party
        )


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
                "created": "2021-01-01T00:00:00+00:00",
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
                "created": "2021-01-01T00:00:00+00:00",
            }
        }
        mock = mocker.Mock(return_value=(1, True))
        mocker.patch("elections.models.Post.objects.update_or_create", mock)
        importer = YNRPostImporter()
        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict)

        mock.assert_called_once_with(
            ynr_id="bar", defaults={"label": "example"}
        )

    def test_post_cache_with_duplicate_ids(self, mocker):
        ballot_dict_one = {
            "post": {
                "id": "foo",
                "slug": "bar",
                "label": "example",
                "created": "date-one",
            }
        }
        ballot_dict_two = {
            "post": {
                "id": "foo",
                "slug": "bar",
                "label": "example",
                "created": "date-two",
            }
        }
        mock = mocker.Mock(return_value=(1, True))
        mocker.patch("elections.models.Post.objects.update_or_create", mock)
        importer = YNRPostImporter()
        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict_one)
        assert len(importer.post_cache) == 1

        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict_two)
        assert len(importer.post_cache) == 2

    def test_post_cache_with_duplicate_slugs(self, mocker):
        ballot_dict_one = {
            "post": {
                "id": None,
                "slug": "bar",
                "label": "example",
                "created": "date-one",
            }
        }
        ballot_dict_two = {
            "post": {
                "id": None,
                "slug": "bar",
                "label": "example",
                "created": "date-two",
            }
        }
        mock = mocker.Mock(return_value=(1, True))
        mocker.patch("elections.models.Post.objects.update_or_create", mock)
        importer = YNRPostImporter()
        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict_one)
        assert len(importer.post_cache) == 1

        importer.update_or_create_from_ballot_dict(ballot_dict=ballot_dict_two)
        assert len(importer.post_cache) == 2
