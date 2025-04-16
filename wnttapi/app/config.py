import os
from datetime import datetime

"""
Wrapper for environment settings used by the app.  We do this here instead of base.py so we 
can raise configuration exceptions, which should not be done in base.py.
"""

# key = year, value = highest predicted tide
YEAR_DATA = None


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


def get_supported_years() -> list:
    if YEAR_DATA is None:
        build_year_config()
    return list(YEAR_DATA.keys())


def get_astro_high_tide(year) -> float:
    if YEAR_DATA is None:
        build_year_config()
    tide = YEAR_DATA.get(year)
    if tide is None:
        raise RuntimeError(f"Tide does not exist for year {year}")
    return tide


def build_year_config():
    global YEAR_DATA
    try:
        valid_years = [int(x) for x in os.environ.get("VALID_YEARS").split(",")]
        astro_tides = [
            float(x) for x in os.environ.get("ASTRONOMICAL_HIGH_TIDES").split(",")
        ]
        if len(valid_years) < 2 or len(valid_years) != len(astro_tides):
            raise RuntimeError(
                "VALID_YEARS and ASTRONOMICAL_HIGH_TIDES missing or invalid"
            )
        YEAR_DATA = {}
        for year, tide in zip(valid_years, astro_tides):
            YEAR_DATA[year] = tide
    except Exception as e:
        raise RuntimeError(
            "VALID_YEARS and ASTRONOMICAL_HIGH_TIDES missing or invalid", e
        )
