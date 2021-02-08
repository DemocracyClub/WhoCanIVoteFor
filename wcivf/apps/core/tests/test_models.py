import pytest
import redis

from core.models import log_postcode, LoggedPostcode


class TestLogPostcode:
    @pytest.fixture(autouse=True)
    def mock_redis(self, mocker):
        mocker.patch("redis.Redis", autospec=True)

    @pytest.fixture(autouse=True)
    def mock_create(self, mocker):
        mocker.patch.object(LoggedPostcode.objects, "create")

    def test_redis_not_used_by_setting(self, settings):
        settings.REDIS_LOG_POSTCODE = False
        postcode = {"postcode": "TE1 1ST"}

        log_postcode(log_dict=postcode)

        LoggedPostcode.objects.create.assert_called_once_with(**postcode)
        redis.Redis.assert_not_called()

    def test_redis_not_used_by_arg(self, settings):
        settings.REDIS_LOG_POSTCODE = True
        postcode = {"postcode": "TE1 1ST"}

        log_postcode(log_dict=postcode, blocking=True)

        LoggedPostcode.objects.create.assert_called_once_with(**postcode)
        redis.Redis.assert_not_called()

    def test_redis_used(self, settings):
        settings.REDIS_LOG_POSTCODE = True
        postcode = {"postcode": "TE1 1ST"}

        log_postcode(log_dict=postcode)

        LoggedPostcode.objects.create.assert_not_called()
        redis.Redis.assert_called_once()
        redis.Redis.return_value.zadd.assert_called_once()
