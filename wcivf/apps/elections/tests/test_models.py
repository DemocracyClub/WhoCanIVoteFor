import datetime
import pytest

from elections.models import Election
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
