import pytest
from parishes.models import ParishCouncilElection


class TestParishCouncilElection:
    @pytest.fixture
    def obj(self):
        return ParishCouncilElection()

    @pytest.mark.freeze_time("2021-05-06")
    def test_in_past_false(self, obj):
        assert obj.in_past is False

    @pytest.mark.freeze_time("2021-05-07")
    def test_in_past_true(self, obj):
        assert obj.in_past is True
