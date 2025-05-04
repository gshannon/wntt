import os
from datetime import datetime, date
import logging
from app.datasource import astro_annual, astrotide


"""
Wrapper for environment settings used by the app.  We do this here instead of base.py so we 
can raise configuration exceptions, which should not be done in base.py.
"""

logger = logging.getLogger(__name__)

# key = year, value = highest predicted tide
YEAR_DATA = None


def get_supported_years() -> list:
    """
    Get the years the API supports, in order. We only support the last 2 years, the current year, and the
    next 2 years.
    """
    year = date.today().year
    return [y for y in range(year - 2, year + 3)]


def get_mllw_conversion() -> float:
    try:
        return float(os.environ.get("NAVD88_MLLW_CONVERSION"))
    except Exception as e:
        raise RuntimeError("NAVD88_MLLW_CONVERSION missing or invalid", e)


def get_mean_high_water() -> float:
    try:
        return float(os.environ.get("MEAN_HIGH_WATER"))
    except Exception as e:
        raise RuntimeError("MEAN_HIGH_WATER missing or invalid", e)


def get_record_tide() -> float:
    try:
        return float(os.environ.get("RECORD_TIDE"))
    except Exception as e:
        raise RuntimeError("RECORD_TIDE missing or invalid", e)


def get_record_tide_date() -> str:
    try:
        return datetime.strptime(os.environ.get("RECORD_TIDE_DATE"), "%m/%d/%Y")
    except Exception as e:
        raise RuntimeError("RECORD_TIDE_DATE missing or invalid", e)


def get_astro_high_tide(year) -> float:
    global YEAR_DATA

    if YEAR_DATA is None:
        YEAR_DATA = astro_annual.read_highest_predicted()
    high = YEAR_DATA.get(year, None)
    if high is None:
        # Load the data, persist it, and refresh memory cache.
        logger.warning(f"Tide was not found for year {year}, pulling from API.")
        high = astrotide.get_astro_highest(year)
        astro_annual.write_highest_predicted(year, high)
        YEAR_DATA = astro_annual.read_highest_predicted()
    return high
