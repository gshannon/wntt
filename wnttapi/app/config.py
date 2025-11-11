import json
import logging
import os
from datetime import date

from app import util
from django.conf import settings


"""
Wrapper for environment settings used by the app.  We do this here instead of base.py so we 
can raise configuration exceptions, which should not be done in base.py.
"""

logger = logging.getLogger(__name__)


def get_version() -> str:
    """Read the version json file which should look this: {"version":"3.04"}

    Raises:
        RuntimeError: if path cannot be found or json is invalid

    Returns:
        str: the version string
    """
    try:
        path = os.path.join(settings.BASE_DIR, "version.json")
        contents = util.read_file(path)
        parsed = json.loads(contents)
        return parsed["version"]
    except Exception as e:
        logger.error(f"Could not read or parse {path}", exc_info=e)
        raise RuntimeError("Could not determine release version")


def get_supported_years() -> list:
    """
    Get the years the API supports, in order. We only support the last 2 years, the current year, and the
    next 2 years. Note that the APP has the same logic, so they should be kept in sync.
    """
    year = date.today().year
    return [y for y in range(year - 2, year + 3)]
