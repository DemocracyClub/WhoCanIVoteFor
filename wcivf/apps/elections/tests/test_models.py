import datetime
import pytest

from elections.models import Election, Post
from elections.tests.factories import PostElectionFactory, PostFactory
from django.test import TestCase


class TestElectionModel(TestCase):
    def setUp(self):
        self.election = Election(slug="not.city-of-london")
        self.city_of_london_election = Election(slug="local.city-of-london")

    def test_in_past(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        election = Election(election_date=yesterday)

        assert election.in_past is True

    def test_is_city_of_london(self):
        assert self.election.is_city_of_london is False
        assert self.city_of_london_election.is_city_of_london is True

    def test_polls_close(self):
        assert self.election.polls_close == datetime.time(22, 00)
        assert self.city_of_london_election.polls_close == datetime.time(20, 0)

    def test_polls_open(self):
        assert self.election.polls_open == datetime.time(7, 00)
        assert self.city_of_london_election.polls_open == datetime.time(8, 0)

    @pytest.mark.freeze_time("2021-05-06")
    def test_is_election_day(self):
        today = Election(election_date=datetime.date(2021, 5, 6))
        future = Election(election_date=datetime.date(2021, 5, 7))
        past = Election(election_date=datetime.date(2021, 5, 5))

        assert today.is_election_day is True
        assert future.is_election_day is False
        assert past.is_election_day is False


class TestPostModel:
    @pytest.mark.parametrize(
        "division_type, description", Post.DIVISION_TYPE_CHOICES
    )
    def test_division_description(self, division_type, description):
        """
        Test that for each division type choice, the correct description is
        returned
        """
        post = PostFactory.build(division_type=division_type)

        assert post.division_description == description

    def test_division_suffix(self, mocker):
        description = mocker.PropertyMock(return_value="Foo Bar Division")
        mocker.patch.object(Post, "division_description", new=description)
        post = PostFactory.build()

        assert post.division_suffix == "division"
        description.assert_called_once()

    def test_full_label(self, mocker):
        suffix = mocker.PropertyMock(return_value="ward")
        mocker.patch.object(Post, "division_suffix", new=suffix)
        post = PostFactory.build(label="Ecclesall")
        assert post.full_label == "Ecclesall ward"
        suffix.assert_called_once()

    @pytest.mark.parametrize(
        "org_type,expected", [("police-area", True), ("another", False)]
    )
    def test_is_police_area(self, org_type, expected):
        post = PostFactory.build(organization_type=org_type)
        assert post.is_police_area == expected

    @pytest.mark.parametrize(
        "suffix, expected",
        [
            ("Police", "Police force area"),
            ("Constabulary", "Constabulary Police force area"),
        ],
    )
    def test_label_for_police_area(self, suffix, expected):
        label = f"South Yorkshire {suffix}"
        post = PostFactory.build(label=label)
        assert post._label_for_police_area == f"South Yorkshire {expected}"


class TestPostElectionModel:
    @pytest.fixture
    def post_election(self):
        return PostElectionFactory.build(election__any_non_by_elections=True)

    @pytest.mark.parametrize(
        "ballot_paper_id,expected",
        [("mayor.of.london", True), ("an.other.election", False)],
    )
    def test_is_mayoral(self, post_election, ballot_paper_id, expected):
        post_election.ballot_paper_id = ballot_paper_id
        assert post_election.is_mayoral == expected

    def test_friendly_name_mayoral(self, post_election):
        post_election.ballot_paper_id = "mayor.of.london"
        assert (
            post_election.friendly_name
            == post_election.election.nice_election_name
        )

    def test_friendly_name(self, post_election):
        assert post_election.friendly_name == post_election.post.full_label

    @pytest.mark.parametrize(
        "ballot_paper_id,expected",
        [("gla.a.2021-05-06", True), ("an.other.election", False)],
    )
    def test_is_london_assembly_additional(
        self, post_election, ballot_paper_id, expected
    ):
        post_election.ballot_paper_id = ballot_paper_id
        assert post_election.is_london_assembly_additional == expected

    def test_friendly_name_london_assembly_additonal(self, post_election):
        post_election.ballot_paper_id = "gla.a.2021-05-06"
        assert post_election.friendly_name == "Additional members"
