import pytest

from parishes.importers import ParishCouncilElectionImporter


class TestImporterCleanMethods:
    @pytest.fixture
    def importer(self):
        return ParishCouncilElectionImporter(url="")

    def test_clean_is_contested(self, importer, subtests):
        cases = [
            ("y", True),
            ("yes", True),
            ("YES", True),
            ("Y", True),
            ("no", False),
            ("n", False),
            ("NO", False),
            ("N", False),
            ("", None),
            ("Something else", None),
        ]
        for case in cases:
            with subtests.test(msg=case[0]):
                result = importer.clean_is_contested(value=case[0])
                assert result is case[1]

    def test_clean_num_ward_seats(self, importer, subtests):
        int_nums = [(n, n) for n in range(10)]
        string_nums = [(str(n), n) for n in range(10)]
        cases = int_nums + string_nums + [(None, 0), ("Something else", 0)]
        for case in cases:
            with subtests.test(msg=case[0]):
                result = importer.clean_num_ward_seats(value=case[0])
                assert result is case[1]

    def test_clean_precept(self, importer, subtests):
        cases = ["£100", "100", "  100  "]
        for case in cases:
            with subtests.test(msg=case):
                assert importer.clean_precept(case) == "100"
