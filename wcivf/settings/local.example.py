DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "wcivf",
        "USER": "wcivf",
        "PASSWORD": "wcivf",
    }
}


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

ALLOWED_HOSTS = ["*"]

YNR_BASE = "https://candidates.democracyclub.org.uk"

EE_BASE = "https://elections.democracyclub.org.uk"

INTERNAL_IPS = ["127.0.0.1"]

SECRET_KEY = "not_for_production"

DEBUG = True

EMAIL_SIGNUP_BACKEND = "local_db"

# SHOW_GB_ID_MESSAGING = False
# SHOW_RESULTS_CHART = False

# These example paths should only be necessary for M1 Mac users

# GDAL_LIBRARY_PATH = "/opt/homebrew/Cellar/gdal/3.5.1_3/lib/libgdal.dylib"

# GEOS_LIBRARY_PATH= '/opt/homebrew/Cellar/geos/3.11.0/lib/libgeos_c.1.17.0.dylib'

SHOW_UPCOMING_ELECTIONS = True
