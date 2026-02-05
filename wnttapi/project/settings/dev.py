# Do not delete this import -- it brings in the base settings
from .base import *
from pathlib import Path

DEBUG = True  # True = INFO and higher go to the console; False = ERROR and higher

ALLOWED_HOSTS = [
    "localhost",
]

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# This maps to the wntt directory.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # This is the only version that works for dealing with migrations from command line, not using a docker container.
        # Do not check it in, as it will break the app in docker.
        # "NAME": str(BASE_DIR / "datamount" / "db" / "wntt.sqlite3"),
        # This version must be used by the app.
        "NAME": "/data/db/wntt.sqlite3",
    }
}


LOGGING = {
    # Use v1 of the logging config schema
    "version": 1,
    # Continue to use existing loggers
    "disable_existing_loggers": False,
    # Create a log handler that prints logs to the terminal
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        # "app.datasource.astrotide": {
        #     "handlers": ["console"],
        #     "level": "DEBUG",
        #     "propagate": False,
        # },
        # "app.graphutil": {
        #     "handlers": ["console"],
        #     "level": "DEBUG",
        #     "propagate": False,
        # },
    },
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {process:d} {module} {funcName} {message}",
            "style": "{",
        },
    },
}
