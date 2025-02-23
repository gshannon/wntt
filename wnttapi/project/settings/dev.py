# Do not delete this import -- it brings in the base settings
from .base import *

DEBUG = True  # True = INFO and higher go to the console; False = ERROR and higher

ALLOWED_HOSTS = [
    "localhost",
]

LOGGING = {
    # Use v1 of the logging config schema
    'version': 1,
    # Continue to use existing loggers
    'disable_existing_loggers': False,
    # Create a log handler that prints logs to the terminal
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        # 'app.datasource.surge': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        #     'propagate': False,
        # },
    },
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {process:d} {module} {funcName} {message}',
            'style': '{',
        },
    },
}
