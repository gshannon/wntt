import logging
import os
import json
from datetime import date
from django.conf import settings

from app import util
from app.datasource import astrotide

"""
Wrapper for environment settings used by the app.  We do this here instead of base.py so we 
can raise configuration exceptions, which should not be done in base.py.
"""

logger = logging.getLogger(__name__)

# These are all the highest predicted annual tides. It will need to be refreshed some day if this lives on.
# key = year, value = highest predicted tide in feet relative to NAVD88.
_annual_highs_navd88 = {
    "8419317": {
        2023: 6.01,
        2024: 6.12,
        2025: 6.18,
        2026: 6.13,
        2027: 6.02,
        2028: 6.16,
        2029: 6.33,
        2030: 6.32,
        2031: 6.29,
        2032: 6.1,
        2033: 6.32,
    },
    "8658163": {
        2025: 3.01,  # TODO: This is MADE UP for now!
    },
}

# Feet to add to navd88 to get mllw, by NOAA station. Keep in sync with front end code.
_navd88_to_mllw = {
    "8419317": 5.14,
    "8658163": 2.75,
}


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


def get_mllw_conversion(noaa_station_id: str) -> float:
    if noaa_station_id in _navd88_to_mllw:
        return _navd88_to_mllw[noaa_station_id]
    raise RuntimeError(f"navd88 conversion missing for station {noaa_station_id}")


def get_astro_high_tide_mllw(year: int, noaa_station_id: str) -> float:
    global _annual_highs_navd88

    if year not in get_supported_years():
        # This should never happen since it would have been caught long before this point.
        raise RuntimeError(f"Year {year} is not supported")

    if (
        noaa_station_id not in _annual_highs_navd88
        or year not in _annual_highs_navd88[noaa_station_id]
    ):
        # Load the data & save it to cache.
        logger.warning(f"Tide was not found for year {year}, pulling from API.")
        high = astrotide.get_astro_highest_navd88(year, noaa_station_id)
        _annual_highs_navd88[noaa_station_id][year] = high

    return util.navd88_feet_to_mllw_feet(
        _annual_highs_navd88[noaa_station_id][year], noaa_station_id
    )
