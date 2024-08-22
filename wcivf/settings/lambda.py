import os

from .base import *  # noqa

DATABASES["default"] = {  # noqa
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("RDS_DB_NAME"),
    "USER": "wcivf",
    "PASSWORD": os.environ.get("RDS_DB_PASSWORD"),
    "HOST": os.environ.get("RDS_HOST"),
    "PORT": os.environ.get("RDS_DB_PORT", "5432"),
}
EE_BASE = "https://elections.democracyclub.org.uk"
