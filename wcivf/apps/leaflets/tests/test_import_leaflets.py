import zoneinfo
from datetime import datetime

import pytest
from leaflets.management.commands.import_leaflets import Command


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
