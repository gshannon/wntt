import json
import logging
import os
import pathlib
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from django.core.cache import cache
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from app import util

logger = logging.getLogger(__name__)
_default_file_dir = "/data/stations"
_default_file_name = "stations.json"


class Station(BaseModel):
    """Class representation of a SWMP station and all its configuration properties. We don't use
    most of these fields in the backend but this allows us to validate everything from the json.
    Aliases are used for returning the data to api clients, in camel case.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(min_length=1, max_length=7)
    time_zone: ZoneInfo = Field(alias="timeZone")
    reserve_name: str = Field(alias="reserveName", min_length=1, max_length=16)
    reserve_url: str = Field(alias="reserveUrl")
    water_station_name: str = Field(alias="waterStationName")
    weather_station_id: str = Field(alias="weatherStationId")
    weather_station_name: str = Field(alias="weatherStationName")
    noaa_station_id: str = Field(alias="noaaStationId", min_length=7, max_length=10)
    noaa_station_name: str = Field(alias="noaaStationName")
    noaa_station_location: dict[str, float] = Field(alias="noaaStationLocation")
    navd88_to_mllw_conversion: float = Field(alias="navd88ToMllwConversion")
    mean_high_water_mllw: float = Field(alias="meanHighWaterMllw")
    map_bounds: list[tuple[float, float]] = Field(alias="mapBounds")
    swmp_location: dict[str, float] = Field(alias="swmpLocation")
    weather_location: dict[str, float] = Field(alias="weatherLocation")
    record_tide_navd88: float = Field(alias="recordTideNavd88")
    record_tide_date: date = Field(alias="recordTideDate")
    min_date_override: date | None = Field(alias="minDateOverride", default=None)

    def navd88_feet_to_mllw_feet(self, nav_feet: float) -> float:
        return round(nav_feet + self.navd88_to_mllw_conversion, 2)


class AllStationsRecord(BaseModel):
    """This class maps the station json file and provides validation"""

    model_config = ConfigDict(frozen=True)
    data: dict[str, Station]


# Get a Station object for a given station id.  The station id is actually the water quality station id,
# such as 'welinwq' for Wells.
def get_station(
    station_id: str,
    data_dir: str = _default_file_dir,
    file_name: str = _default_file_name,
    force_reload: bool = False,
) -> Station:
    stations = get_all_stations(data_dir, file_name, force_reload)
    if station_id not in stations:
        raise util.InternalError(f"Station ID {station_id} not found")
    return stations[station_id]


def get_station_with_noaa_id(
    noaa_station_id: str,
    data_dir: str = _default_file_dir,
    file_name: str = _default_file_name,
    force_reload: bool = False,
) -> Station:
    stations = get_all_stations(data_dir, file_name, force_reload)
    for stn in stations.values():
        if stn.noaa_station_id == noaa_station_id:
            return stn
    raise util.InternalError(f"Station with NOAA id {noaa_station_id} not found!")


def get_astro_high_tide_mllw(
    station: Station, year: int, data_dir: str = _default_file_dir
) -> float | None:
    data = get_or_load_annual_highs(data_dir)
    year_str = str(year)

    if station.noaa_station_id not in data:
        msg = f"No annual highs found for station {station.noaa_station_id}"
        logger.error(msg)
        return None

    if year_str not in data[station.noaa_station_id]:
        msg = f"No annual high found for {station.noaa_station_id} for {year}"
        logger.error(msg)
        return None

    navd88_high = data[station.noaa_station_id][year_str]
    logger.debug(
        f"for station {station.noaa_station_id} year {year_str}, navd88 high: {navd88_high}"
    )
    return station.navd88_feet_to_mllw_feet(navd88_high)


def get_all_stations(
    data_dir: str = _default_file_dir,
    file_name: str = _default_file_name,
    force_reload: bool = False,
) -> dict[str, Station]:
    """Get the cached stations, or load them from the json file if not cached yet."""
    cache_key = "swmp_stations_cls"
    data = cache.get(cache_key)
    if data is not None and not force_reload:
        return data

    filepath = os.path.join(data_dir, file_name)
    json_content = pathlib.Path(filepath).read_text()

    try:
        allStations = AllStationsRecord.model_validate_json(json_content, strict=True)
        cache.set(
            cache_key, allStations.data, timeout=None
        )  # Cache for as long as the server is running
        logger.debug(
            f"Loaded {len(allStations.data)} stations from disk and cached with key {cache_key}"
        )
        return allStations.data
    except ValidationError as ve:
        raise util.InternalError("Station json validation error") from ve


def get_all_stations_api(
    data_dir: str = _default_file_dir,
    file_name: str = _default_file_name,
    force_reload: bool = False,
) -> dict[str, dict[str, Any]]:
    cache_key = "swmp_stations_dict"
    data = cache.get(cache_key)
    if data is not None and not force_reload:
        return data

    filepath = os.path.join(data_dir, file_name)
    json_content = pathlib.Path(filepath).read_text()

    try:
        allStations = AllStationsRecord.model_validate_json(json_content, strict=True)
        # Create a dict that can be returned to the api caller. We use the alias field names which are camel case
        # and use json mode so it handles the ZoneInfo.
        stations_dict = AllStationsRecord.model_dump(
            allStations, by_alias=True, mode="json"
        )
        cache.set(cache_key, stations_dict["data"], timeout=None)
        return stations_dict["data"]
    except ValidationError as ve:
        raise util.InternalError("Station json validation error") from ve


def get_or_load_annual_highs(
    data_dir: str = _default_file_dir,
) -> dict[str, dict[str, float]]:
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
        logger.error("Error loading annual highs from %s: %s", filepath, str(e))
        return {}
