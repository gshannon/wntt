# Do not delete this import -- it brings in the base settings
from .base import *

"""
Might want to consider these some day
- EMAIL_BACKEND
- DEFAULT_FROM_EMAIL
- SERVER_EMAIL
- STATIC_ROOT
- STATIC_URL
- CSRF_COOKIE_SECURE
"""

DEBUG = False  # ERROR and higher go to the console

ALLOWED_HOSTS = [
    os.environ.get("API_ALLOWED_HOST"),
]

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/data/db/wntt.sqlite3",
    }
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "my-format",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "/var/log/wntt/django.log",
            "formatter": "my-format",
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "WARNING"),
            "propagate": False,
        },
    },
    "formatters": {
        "my-format": {
            "format": "{asctime} {levelname} {process:d} {module} {funcName} {message}",
            "style": "{",
        },
    },
}
