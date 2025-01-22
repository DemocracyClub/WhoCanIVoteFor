# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import contextlib
import os
import sys

import dc_design_system
import requests
import sentry_sdk.integrations.django
from dc_logging_client import DCWidePostcodeLoggingClient
from dc_utils.settings.pipeline import *  # noqa
from dc_utils.settings.pipeline import get_pipeline_settings
from dc_utils.settings.whitenoise import whitenoise_add_middleware

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def here(*x):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)


PROJECT_ROOT = here("..")


def root(*x):
    return os.path.join(os.path.abspath(PROJECT_ROOT), *x)


def repo_root(*x):
    return os.path.join(os.path.abspath(here("../..")), *x)


# Add apps to the PYTHON PATH
sys.path.insert(0, root("apps"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")
ADMINS = (("WCIVF Developers", "developers@democracyclub.org.uk"),)
MANAGERS = ADMINS

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


def get_ec2_ip():
    token_req = requests.put(
        "http://169.254.169.254/latest/api/token",
        headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
        timeout=2,
    )
    token_req.raise_for_status()
    token_req.text
    ip_req = requests.get(
        "http://169.254.169.254/latest/meta-data/local-ipv4",
        headers={"X-aws-ec2-metadata-token": token_req.text},
        timeout=2,
    )
    ip_req.raise_for_status()
    return ip_req.text


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
]

if os.environ.get("DC_ENVIRONMENT") and os.environ.get("FQDN"):
    ALLOWED_HOSTS.append(os.environ.get("FQDN"))
    ALLOWED_HOSTS.append(get_ec2_ip())


CSRF_TRUSTED_ORIGINS = [
    f"https://{os.environ.get('FQDN')}",
]

SECURE_PROXY_SSL_HEADER = ("HTTP_CLOUDFRONT_FORWARDED_PROTO", "https")

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
    "django_filters",
    "dc_utils",
    "pipeline",
    "elections",
    "core",
    "people",
    "parties",
    "profiles",
    "feedback",
    "hustings",
    "peoplecvs",
    "leaflets",
    "django_extensions",
    "rest_framework",
    "api",
    "pledges",
    "news_mentions",
    "dc_design_system",
    "referendums",
    "parishes",
    "ppc_2024",
    "administrations",
)

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.UTMTrackerMiddleware",
    "dc_utils.middleware.BasicAuthMiddleware",
)

MIDDLEWARE = whitenoise_add_middleware(MIDDLEWARE)

# When defining a model, if no field in a model is defined with primary_key=True
# an implicit primary key is added. The type of this implicit primary key can
# now be controlled via the DEFAULT_AUTO_FIELD setting and AppConfig.default_auto_field
# attribute. No more needing to override primary keys in all models.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

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
                "core.context_processors.use_compress_css",
                "core.context_processors.postcode_form",
                "core.context_processors.referer_postcode",
                "core.context_processors.use_i18n",
                "hustings.context_processors.show_hustings_cta",
                "feedback.context_processors.feedback_form",
                "dealer.contrib.django.context_processor",
                "dc_utils.context_processors.dc_django_utils",
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
        "NAME": "wcivf",
        "USER": "",
        "PASSWORD": "",
    }
}
DATABASE_ROUTERS = []
if int(os.environ.get("FEEDBACK_DB_ENABLED", "0")):
    DATABASES["feedback"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("FEEDBACK_DB_NAME", "wcivf_feedback_production"),
        "USER": "postgres",
        "PASSWORD": os.environ.get("FEEDBACK_DB_PASSWORD"),
        "HOST": os.environ.get("FEEDBACK_DB_HOST"),
        "PORT": "",
    }

    if os.environ.get("DC_ENVIRONMENT") in ["production"]:
        DATABASE_ROUTERS.append("core.db_routers.FeedbackRouter")

if not os.environ.get("IGNORE_ROUTERS") and os.environ.get(
    "RDS_DB_NAME", False
):
    DATABASE_ROUTERS.append("core.db_routers.PrincipalRDSRouter")
    DATABASES["principal"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("RDS_DB_NAME"),
        "USER": "wcivf",
        "PASSWORD": os.environ.get("RDS_DB_PASSWORD"),
        "HOST": os.environ.get("RDS_HOST"),
        "PORT": "",
    }

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = "en-gb"
LANGUAGES = [
    ("en", "English"),
    ("cy", "Welsh"),
]
LOCALE_PATHS = (repo_root("locale"),)

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Homepage feature switches
SHOW_GB_ID_MESSAGING = False
SHOW_RESULTS_CHART = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = "/static/"

STATICFILES_DIRS = (root("assets"),)
STATIC_ROOT = root("static")

PIPELINE = get_pipeline_settings(
    extra_css=["scss/style.scss"],
    extra_js=["feedback/js/feedback_form.js"],
)

PIPELINE["SASS_ARGUMENTS"] += (
    " -I " + dc_design_system.DC_SYSTEM_PATH + "/system"
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

YNR_API_KEY = os.environ.get("YNR_API_KEY", None)
YNR_BASE = "https://candidates.democracyclub.org.uk"
YNR_UTM_QUERY_STRING = "utm_source=who&utm_campaign=ynr_cta"
EE_BASE = "https://elections.democracyclub.org.uk"
DEVS_DC_BASE = os.environ.get(
    "DEVS_DC_BASE", "https://developers.democracyclub.org.uk"
)
DEVS_DC_API_KEY = os.environ.get("DEVS_DC_API_KEY", None)

WDIV_BASE = "http://wheredoivote.co.uk"
WDIV_API = "/api/beta"

CANONICAL_URL = "https://whocanivotefor.co.uk"
ROBOTS_USE_HOST = False
USE_X_FORWARDED_HOST = True

EMAIL_SIGNUP_BACKEND = "event_bridge"
EMAIL_SIGNUP_BACKEND_KWARGS = {
    "source": "WCIVF",
    "bus_arn": os.environ.get("EMAIL_SIGNUP_EVENT_BRIDGE_ARN"),
}

# DC Base Theme settings
SITE_TITLE = "Who Can I Vote For?"

AKISMET_API_KEY = os.environ.get("AKISMET_API_KEY")

AKISMET_BLOG_URL = CANONICAL_URL

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

PARTY_LIST_VOTING_TYPES = ["PR-CL", "AMS"]

WDIV_API_KEY = os.environ.get("WDIV_API_KEY")
SLACK_FEEDBACK_WEBHOOK_URL = os.environ.get("SLACK_FEEDBACK_WEBHOOK_URL")  # noqa

CHECK_HOST_DIRTY = False
DIRTY_FILE_PATH = "~/server_dirty"

if os.environ.get("DC_ENVIRONMENT"):
    CHECK_HOST_DIRTY = True

    import sentry_sdk
    from sentry_sdk.integrations import aws_lambda, django
    from sentry_sdk.integrations.logging import ignore_logger

    ignore_logger("django.security.DisallowedHost")

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN"),
        integrations=[
            django.DjangoIntegration(),
            aws_lambda.AwsLambdaIntegration(timeout_warning=True),
        ],
        environment=os.environ.get("DC_ENVIRONMENT"),
    )


# DC Logging Client
LOGGER_ARN = os.environ.get("LOGGER_ARN", None)
firehose_args = {"function_arn": LOGGER_ARN} if LOGGER_ARN else {"fake": True}
POSTCODE_LOGGER = DCWidePostcodeLoggingClient(**firehose_args)

SHOW_HUSTINGS_CTA = False
ENABLE_LAYERS_OF_STATE_FEATURE = os.environ.get(
    "ENABLE_LAYERS_OF_STATE_FEATURE", False
)

BASIC_AUTH_ALLOWLIST = ["/_status_check/"]

with contextlib.suppress(ImportError):
    # .local.py overrides all the common settings.
    from .local import *  # noqa

    if DEBUG:
        INSTALLED_APPS += ("debug_toolbar",)
        MIDDLEWARE += ("debug_toolbar.middleware.DebugToolbarMiddleware",)

if os.environ.get("CIRCLECI"):
    with contextlib.suppress(ImportError):
        from .ci import *  # noqa
