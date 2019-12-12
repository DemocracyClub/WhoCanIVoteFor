# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
here = lambda *x: os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)
PROJECT_ROOT = here("..")
root = lambda *x: os.path.join(os.path.abspath(PROJECT_ROOT), *x)

# Add apps to the PYTHON PATH
sys.path.insert(0, root("apps"))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "1$s^ggnnc16*_9=a^5yv3jr4pw3a=f##c#fc!ewc&i5n^q88l%"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

SITE_ID = 1

# Application definition

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "dc_theme",
    "dc_signup_form",
    "pipeline",
    "elections",
    "markdown_deux",
    "core",
    "people",
    "parties",
    "profiles",
    "feedback",
    "hustings",
    "peoplecvs",
    "leaflets",
    "debug_toolbar",
    "django_extensions",
    "rest_framework",
    "robots",
    "api",
    "results",
    "donations",
    "pledges",
    "news_mentions",
)

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.UTMTrackerMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)

ROOT_URLCONF = "wcivf.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [root("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dc_theme.context_processors.dc_theme_context",
                "dc_signup_form.context_processors.signup_form",
                "core.context_processors.canonical_url",
                "core.context_processors.site_title",
                "core.context_processors.use_compress_css",
                "core.context_processors.postcode_form",
                "core.context_processors.referer_postcode",
                "feedback.context_processors.feedback_form",
                "dealer.contrib.django.context_processor",
            ]
        },
    }
]

USE_COMPRESSED_CSS = False
MEDIA_ROOT = root("media")
MEDIA_URL = "/media/"

WSGI_APPLICATION = "wcivf.wsgi.application"


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "",
        "USER": "postgres",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = "en-gb"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_DIRS = (root("assets"),)
STATIC_ROOT = root("static")

from dc_theme.settings import get_pipeline_settings
from dc_theme.settings import STATICFILES_FINDERS  # noqa

STATICFILES_STORAGE = "pipeline.storage.PipelineCachedStorage"

PIPELINE = get_pipeline_settings(
    extra_css=["scss/main.scss"],
    extra_js=["js/scripts.js", "feedback/js/feedback_form.js"],
)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_CACHE_ALIAS = "default"

YNR_BASE = "https://candidates.democracyclub.org.uk"
YNR_UTM_QUERY_STRING = "utm_source=who&utm_campaign=ynr_cta"
EE_BASE = "https://elections.democracyclub.org.uk"

WDIV_BASE = "https://wheredoivote.co.uk"
WDIV_API = "/api/beta"

CANONICAL_URL = "https://whocanivotefor.co.uk"
ROBOTS_USE_HOST = False

EMAIL_SIGNUP_ENDPOINT = (
    "https://democracyclub.org.uk/mailing_list/api_signup/v1/"
)
EMAIL_SIGNUP_API_KEY = ""

# DC Base Theme settings
SITE_TITLE = "Who Can I Vote For?"
SITE_LOGO = "images/logo.png"
SITE_LOGO_WIDTH = "440px"

import redis

REDIS_POOL = redis.ConnectionPool(host="127.0.0.1", port=6379, db=5)
REDIS_KEY_PREFIX = "WCIVF"

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": ["api.permissions.ReadOnly"],
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework_jsonp.renderers.JSONPRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

GO_CARDLESS_PAYMENT_NAME = "Democracy Club Donation"
GO_CARDLESS_PAYMENT_DESCRIPTION = (
    "Helping Democracy Club "
    "increase the quality of information on elections & the democratic processes"
)

GOCARDLESS_REDIRECT_URL = "https://whocanivotefor.co.uk/donate/process/"

PARTY_LIST_VOTING_TYPES = ["PR-CL"]

# .local.py overrides all the common settings.
try:
    from .local import *  # noqa
except ImportError:
    pass

if os.environ.get("TRAVIS") or os.environ.get("CIRCLECI"):
    try:
        from .ci import *  # noqa
    except ImportError:
        pass
