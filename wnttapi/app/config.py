import logging
import os
from datetime import date, datetime

from app.datasource import astrotide

"""
Wrapper for environment settings used by the app.  We do this here instead of base.py so we 
can raise configuration exceptions, which should not be done in base.py.
"""

logger = logging.getLogger(__name__)

# This is a cache of the highest predicted tide for each year. It is populated as needed.
# Worker processes will not share the cache, but this is acceptable because the the processes should be
# long-lived, and loading should only happen the first time the year is requested for any worker.
# key = year, value = highest predicted tide in feet relative to MLLW
_annual_highest = {}


def get_supported_years() -> list:
    """
    Get the years the API supports, in order. We only support the last 2 years, the current year, and the
    next 2 years. Note that the APP has the same logic, so they should be kept in sync.
    """
    year = date.today().year
    return [y for y in range(year - 2, year + 3)]


def get_mllw_conversion() -> float:
    try:
        return float(os.environ.get("NAVD88_MLLW_CONVERSION"))
    except Exception as e:
        raise RuntimeError("NAVD88_MLLW_CONVERSION missing or invalid", e)


def get_mean_high_water_mllw() -> float:
    try:
        return float(os.environ.get("MEAN_HIGH_WATER_MLLW"))
    except Exception as e:
        raise RuntimeError("MEAN_HIGH_WATER_MLLW missing or invalid", e)


def get_record_tide_navd88() -> float:
    try:
        return float(os.environ.get("RECORD_TIDE_NAVD88"))
    except Exception as e:
        raise RuntimeError("RECORD_TIDE_NAVD88 missing or invalid", e)


def get_record_tide_date() -> str:
    try:
        return datetime.strptime(os.environ.get("RECORD_TIDE_DATE"), "%m/%d/%Y")
    except Exception as e:
        raise RuntimeError("RECORD_TIDE_DATE missing or invalid", e)


def get_astro_high_tide_mllw(year) -> float:
    global _annual_highest

    if year not in get_supported_years():
        # This should never happen since it would have been caught long before this point.
        raise RuntimeError(f"Year {year} is not supported")

    if year not in _annual_highest:
        # Load the data & save it to cache.
        logger.info(f"Tide was not found for year {year}, pulling from API.")
        high = astrotide.get_astro_highest(year)
        _annual_highest[year] = high

    return _annual_highest[year]
