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
        # Temporarily use this NAME for "makemigrations" since that must be done directly on the
        # file system, not docker container, so the created migration file persists.
        # "NAME": str(BASE_DIR / "datamount" / "db" / "wntt.sqlite3"),
        # Otherwise, use this NAME, which uses a docker mount for running the container.
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
