import json
import logging
import os
from datetime import date
from zoneinfo import ZoneInfo

from app import util
from django.core.cache import cache
import sentry_sdk

logger = logging.getLogger(__name__)
_default_file_dir = "/data/stations"

"""Class representation of a SWMP station and all its configuration properties. The fields 
are a subset of the properties contained in the stations.json file. Only those needed for 
backend processing are included here.
"""


class Station:
    # Builder method
    @staticmethod
    def from_dict(station_id: str, data: dict) -> "Station":
        return Station(
            id=station_id,
            weather_station_id=data["weatherStationId"],
            noaa_station_id=data["noaaStationId"],
            navd88_to_mllw=data["navd88ToMllwConversion"],
            time_zone=ZoneInfo(data["timeZone"]),
        )

    def __init__(
        self,
        id: str,
        weather_station_id: str,
        noaa_station_id: str,
        navd88_to_mllw: float,
        time_zone: ZoneInfo,
    ):
        self.id = id
        self.weather_station_id = weather_station_id
        self.noaa_station_id = noaa_station_id
        self.mllw_conversion = navd88_to_mllw
        self.time_zone = time_zone

    def navd88_feet_to_mllw_feet(self, in_value: float) -> float:
        return round(in_value + self.mllw_conversion, 2)

    def mllw_feet_to_navd88_feet(self, in_value: float) -> float:
        return round(in_value - self.mllw_conversion, 2)

    def navd88_meters_to_mllw_feet(self, meters: float) -> float:
        feet = round(meters * 3.28084, 2)
        return round(self.navd88_feet_to_mllw_feet(feet), 2)

    def mllw_feet_to_navd88_meters(self, feet: float) -> float:
        feet = self.mllw_feet_to_navd88_feet(feet)
        return round(feet / 3.28084, 2)


def get_station_selection_data(data_dir=_default_file_dir) -> list:
    """Build list of objects containing info for populating a select list of all stations

    Returns:
        list: list of station selection dicts
    """
    data = get_or_load_stations(data_dir)
    selection_data = []
    for station_id, station in data.items():
        selection_data.append(
            {
                "id": station_id,
                "reserveName": station["reserveName"],
                "waterStationName": station["waterStationName"],
            }
        )
    return selection_data


def get_supported_years() -> list:
    """
    Get the years the API supports, in order. By default this means the last 2 years, the current year,
    plus the next 2 years.
    """
    year = date.today().year
    return [y for y in range(year - 2, year + 3)]


# Get a Station object for a given station id.  The station id is actually the water quality station id,
# such as 'welinwq' for Wells.
def get_station(station_id: str, data_dir=_default_file_dir) -> Station:
    obj = get_station_data(station_id, data_dir=data_dir)
    return Station.from_dict(station_id, obj)


def get_station_data(station_id: str, data_dir=_default_file_dir) -> dict:
    """Get an object with all station info for an id.

    Args:
        station_id (str): station id, e.g. 'welinwq'

    Raises:
        InternalError: if station id not found

    Returns:
        dict: station data object
    """
    data = get_or_load_stations(data_dir)
    if station_id not in data:
        raise util.InternalError(f"Station ID {station_id} not found")
    return data[station_id]


def get_all_stations(data_dir=_default_file_dir) -> dict:
    """Get a list of Station objects

    Args:
        data_dir: override for testing

    Returns:
        list of station data objects
    """
    return get_or_load_stations(data_dir)


def get_astro_high_tide_mllw(
    station: Station, year: int, data_dir=_default_file_dir
) -> float:
    data = get_or_load_annual_highs(data_dir)
    year_str = str(year)

    if station.noaa_station_id not in data:
        msg = "No annual highs found for station %s!" % (station.noaa_station_id)
        logger.error(msg)
        sentry_sdk.capture_message(msg)
        return None

    if year_str not in data[station.noaa_station_id]:
        msg = "No annual high found for station %s for %d" % (
            station.noaa_station_id,
            year,
        )
        logger.error(msg)
        sentry_sdk.capture_message(msg)
        return None

    navd88_high = data[station.noaa_station_id][year_str]
    logger.debug(
        f"for station {station.noaa_station_id} year {year_str}, navd88 high: {navd88_high}"
    )
    return station.navd88_feet_to_mllw_feet(navd88_high)


def get_or_load_stations(data_dir: str = _default_file_dir) -> dict:
    """Get the cached stations, or load them from the json file if not cached yet."""
    cache_key = "stations_data"
    data = cache.get(cache_key)
    if data is not None:
        return data

    filepath = os.path.join(data_dir, "stations.json")
    contents = util.read_file(filepath)
    data = json.loads(contents)
    cache.set(cache_key, data, timeout=None)  # Cache forever
    logger.debug(
        f"Loaded {len(data)} stations from disk and cached with key {cache_key}"
    )
    return data


def get_or_load_annual_highs(
    data_dir: str = _default_file_dir,
) -> dict:
    """Get the cached annual highs, or load them from the json file if not cached yet."""
    cache_key = "annual_highs_navd88"
    data = cache.get(cache_key)
    if data is not None:
        return data

    try:
        filepath = os.path.join(data_dir, "annual_highs_navd88.json")
        contents = util.read_file(filepath)
        data = json.loads(contents)
        cache.set(cache_key, data, timeout=None)  # Cache forever
        logger.debug(
            f"Loaded {len(data)} annual highs from disk and cached with key {cache_key}"
        )
        return data
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error("Error loading annual highs from %s: %s", filepath, str(e))
        return {}
