STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "pipeline.storage.PipelineStorage"},
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "wcivf",
        "USER": "wcivf",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

SECRET_KEY = "just_for_ci"
YNR_API_KEY = None
EE_BASE = "https://elections.democracyclub.org.uk"
