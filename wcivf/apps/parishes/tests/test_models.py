import pytest
from parishes.models import ParishCouncilElection


class TestParishCouncilElection:
    @pytest.fixture
    def obj(self):
        return ParishCouncilElection()

    @pytest.mark.freeze_time("2021-05-06")
    def test_in_past_false(self, obj):
        assert obj.in_past is False

    @pytest.mark.freeze_time("2021-05-06")
    def test_in_past_day_of_ballot(self, obj):
        assert obj.in_past is False

    @pytest.mark.freeze_time("2021-05-07")
    def test_in_past_true(self, obj):
        assert obj.in_past is True

    def test_is_uncontested(self, subtests):
        cases = [
            (ParishCouncilElection(is_contested=True), False),
            (ParishCouncilElection(is_contested=None), False),
            (ParishCouncilElection(is_contested=False), True),
        ]
        for case in cases:
            msg = f"is_contested={case[0].is_contested}"
            with subtests.test(msg=msg):
                assert case[0].is_uncontested is case[1]

    def test_unknown_if_contested(self, subtests):
        cases = [
            (ParishCouncilElection(is_contested=True), False),
            (ParishCouncilElection(is_contested=False), False),
            (ParishCouncilElection(is_contested=None), True),
        ]
        for case in cases:
            msg = f"is_contested={case[0].unknown_if_contested}"
            with subtests.test(msg=msg):
                assert case[0].unknown_if_contested is case[1]
