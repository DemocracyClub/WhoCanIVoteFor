import datetime
from django.utils import timezone
from faker import Faker
import pytest

from elections.models import Election, Post, PostElection
from elections.tests.factories import (
    ElectionFactoryLazySlug,
    ElectionWithPostFactory,
    PostElectionFactory,
    PostFactory,
)
from parties.tests.factories import PartyFactory
from people.tests.factories import PersonFactory, PersonPostFactory


fake = Faker()


class TestElectionModel:
    @pytest.fixture
    def election(self):
        return Election(slug="not.city-of-london")

    @pytest.fixture
    def city_of_london_election(self):
        return Election(slug="local.city-of-london")

    def test_in_past(self):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        election = Election(election_date=yesterday)

        assert election.in_past is True

    def test_is_city_of_london(self, election, city_of_london_election):
        assert election.is_city_of_london is False
        assert city_of_london_election.is_city_of_london is True

    def test_polls_close(self, election, city_of_london_election):
        assert election.polls_close == datetime.time(22, 00)
        assert city_of_london_election.polls_close == datetime.time(20, 0)

    def test_polls_open(self, election, city_of_london_election):
        assert election.polls_open == datetime.time(7, 00)
        assert city_of_london_election.polls_open == datetime.time(8, 0)

    @pytest.mark.freeze_time("2021-05-06")
    def test_is_election_day(self):
        today = Election(election_date=datetime.date(2021, 5, 6))
        future = Election(election_date=datetime.date(2021, 5, 7))
        past = Election(election_date=datetime.date(2021, 5, 5))

        assert today.is_election_day is True
        assert future.is_election_day is False
        assert past.is_election_day is False

    @pytest.mark.parametrize(
        "name,expected",
        [
            (
                "London Assembly Elections (Additional)",
                "London Assembly Elections",
            ),
            (
                "London Assembly Elections (Constituencies)",
                "London Assembly Elections",
            ),
            (
                "Senedd Cymru elections (Constituencies)",
                "Senedd Cymru elections",
            ),
            ("Senedd Cymru elections (Regions)", "Senedd Cymru elections"),
            (
                "Scottish Parliament elections (Constituencies)",
                "Scottish Parliament elections",
            ),
            (
                "Scottish Parliament elections (Regions)",
                "Scottish Parliament elections",
            ),
        ],
    )
    def test_name_without_brackets(self, name, expected):
        election = Election(name=name, any_non_by_elections=True)
        assert election.name_without_brackets == expected

    def test_name_without_brackets_by_election(self, election):
        election.any_non_by_elections = False
        election.name = "Scottish Parliament (Constituencies)"
        expected = "Scottish Parliament by-election"
        assert election.name_without_brackets == expected

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "suffix, expected",
        [
            ("constituency", "constituencies"),
            ("parish", "parishes"),
            ("ward", "wards"),
            ("division", "divisions"),
            ("area", "areas"),
            ("region", "regions"),
            ("", "posts"),
        ],
    )
    def test_pluralized_division_suffix(self, mocker, suffix, expected):
        election = ElectionWithPostFactory()
        mocker.patch.object(
            Post,
            "division_suffix",
            new_callable=mocker.PropertyMock,
            return_value=suffix,
        )

        assert election.pluralized_division_name == expected


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

    @pytest.mark.parametrize(
        "ballot_paper_id,expected",
        [("parl.hallam", True), ("an.other.election", False)],
    )
    def test_is_parliamentary(self, post_election, ballot_paper_id, expected):
        post_election.ballot_paper_id = ballot_paper_id
        assert post_election.is_parliamentary == expected

    def test_friendly_name_mayoral(self, post_election):
        post_election.ballot_paper_id = "mayor.of.london"
        post_election.post.label = "Greater London Authority"
        assert (
            post_election.friendly_name
            == "Greater London Authority mayoral election"
        )

    @pytest.mark.django_db
    def test_is_constituency(self, post_election):
        post_election.ballot_paper_id = "gla.c.2021-05-06"
        assert post_election.is_constituency is True

    @pytest.mark.django_db
    def test_is_regional(self, post_election):
        post_election.ballot_paper_id = "gla.c.2021-05-06"
        assert post_election.is_regional is False

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-04-06")
    def test_past_registration_deadline(self, post_election):
        post = PostFactory(territory="ENG")
        oldest = PostElectionFactory(
            ballot_paper_id="parl.cities-of-london-and-westminster.2019-05-06",
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-6", current=False, election_type="parl"
            ),
        )
        future = PostElectionFactory(
            ballot_paper_id="parl.cities-of-london-and-westminster.2021-05-06",
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6", current=True, election_type="parl"
            ),
        )

        assert oldest.past_registration_deadline is True
        assert future.past_registration_deadline is False

    @pytest.mark.parametrize(
        "label, expected",
        [
            (
                "Avon and Somerset Constabulary",
                "Avon and Somerset Constabulary Police force area",
            ),
            ("North Yorkshire Police", "North Yorkshire Police force area"),
        ],
    )
    def test_friendly_name_pcc(self, post_election, label, expected):
        post_election.ballot_paper_id = "pcc.election"
        post_election.post.label = label
        assert post_election.friendly_name == expected

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

    @pytest.mark.parametrize(
        "org_type,expected", [("pcc.ballot", True), ("not.pcc", False)]
    )
    def test_is_pcc(self, org_type, expected):
        post = PostElectionFactory.build(ballot_paper_id=org_type)
        assert post.is_pcc == expected

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_ballot(self):
        post = PostFactory()
        oldest = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-6", current=False, election_type="local"
            ),
        )
        old = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2020-5-6", current=False, election_type="local"
            ),
        )
        future = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6", current=True, election_type="local"
            ),
        )

        assert oldest.next_ballot == future
        assert old.next_ballot == future
        assert future.next_ballot is None

    @pytest.mark.django_db
    @pytest.mark.freeze_time("2021-5-1")
    def test_next_ballot_different_election_type(self):
        post = PostFactory()
        local = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2019-5-6", current=False, election_type="local"
            ),
        )
        mayoral = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2020-5-6", current=False, election_type="mayor"
            ),
        )
        next_local = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6", current=True, election_type="local"
            ),
        )
        assert local.next_ballot == next_local
        assert mayoral.next_ballot is None

    @pytest.mark.django_db
    def test_party_ballot_count(self):
        post = PostFactory()
        post_election = PostElectionFactory(
            post=post,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6", current=True, election_type="local"
            ),
        )
        people = [PersonFactory() for p in range(5)]
        PersonPostFactory(
            post_election=post_election,
            election=ElectionFactoryLazySlug(
                election_date="2021-5-6",
                current=True,
                election_type="local",
            ),
            person=PersonFactory(),
            party=PartyFactory(party_id="ynmp-party:2"),
        )
        for i, person in enumerate(people):
            PersonPostFactory(
                post_election=post_election,
                election=ElectionFactoryLazySlug(
                    election_date="2021-5-6",
                    current=True,
                    election_type="local",
                ),
                person=person,
                party=PartyFactory(party_id=i),
            )
        assert post_election.party_ballot_count == "1 ballot option"
        post_election.election.uses_lists = True
        post_election.election.save()
        post_election.election.refresh_from_db()
        assert post_election.party_ballot_count == "6 ballot options"

    def test_should_display_sopn_info_in_past(self, post_election):
        post_election.locked = True
        post_election.election.election_date = fake.past_date()
        assert post_election.should_display_sopn_info is False

    def test_should_display_sopn_info_not_in_past(self, post_election):
        post_election.election.election_date = fake.future_date()
        post_election.locked = True
        assert post_election.should_display_sopn_info is True

    def test_should_display_sopn_info_not_in_past_not_locked_no_sopn_date(
        self, post_election, mocker
    ):
        post_election.election.election_date = fake.future_date()
        post_election.locked = False
        mocker.patch.object(
            PostElection,
            "expected_sopn_date",
            new_callable=mocker.PropertyMock,
            return_value=None,
        )
        assert post_election.should_display_sopn_info is False

    def test_should_display_sopn_info_not_in_past_not_locked_with_sopn_date(
        self, post_election, mocker
    ):
        post_election.election.election_date = fake.future_date()
        post_election.locked = False
        mocker.patch.object(
            PostElection,
            "expected_sopn_date",
            new_callable=mocker.PropertyMock,
            return_value=timezone.datetime.now().date(),
        )
        assert post_election.should_display_sopn_info is True

    @pytest.mark.freeze_time("2021-04-09")
    def test_past_expected_sopn_day(self, post_election, mocker, subtests):

        dates = [
            (timezone.datetime(2021, 4, 14).date(), False),
            (timezone.datetime(2021, 1, 1).date(), True),
        ]
        for date in dates:
            with subtests.test(msg=date[0]):
                mocker.patch.object(
                    PostElection,
                    "expected_sopn_date",
                    new_callable=mocker.PropertyMock,
                    return_value=date[0],
                )
                assert post_election.past_expected_sopn_day is date[1]
