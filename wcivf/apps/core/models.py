import json

from django.conf import settings
from django.utils.timezone import now
from django.db import models

from django_extensions.db.models import TimeStampedModel
import redis


class LoggedPostcode(TimeStampedModel):
    postcode = models.CharField(max_length=100)
    utm_source = models.CharField(blank=True, max_length=100, db_index=True)
    utm_medium = models.CharField(blank=True, max_length=100, db_index=True)
    utm_campaign = models.CharField(blank=True, max_length=100, db_index=True)

    def __str__(self):
        return "{0}".format(self.postcode)


def log_postcode(log_dict, blocking=False):
    """
    Take a dict with all the kwargs needed to create a LoggedPostcode
    model and create it or add it to a queue to save later
    """
    if blocking or not settings.REDIS_LOG_POSTCODE:
        return LoggedPostcode.objects.create(**log_dict)

    red = redis.Redis(connection_pool=settings.REDIS_POOL)
    key = "{}:log_postcode_queue".format(settings.REDIS_KEY_PREFIX)

    log_dict["created"] = now().timestamp()

    value = json.dumps(log_dict)
    red.zadd(key, {value: log_dict["created"]})


def write_logged_postcodes():
    red = redis.Redis(connection_pool=settings.REDIS_POOL)
    key = "{}:log_postcode_queue".format(settings.REDIS_KEY_PREFIX)
    score_max = now().timestamp()

    # Get all the items from Redis
    logged_items = red.zrangebyscore(key, 0, score_max, withscores=True)

    # Remove all the items we've seen from Redis
    red.zremrangebyscore(key, 0, score_max)

    postcodes_to_save = []
    for item in logged_items:
        lp = LoggedPostcode(**json.loads(item[0].decode()))

        postcodes_to_save.append(lp)
    LoggedPostcode.objects.bulk_create(postcodes_to_save)
