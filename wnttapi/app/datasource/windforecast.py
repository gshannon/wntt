import json
import logging
from datetime import datetime, timedelta, tzinfo
from typing import TypedDict
from zoneinfo import ZoneInfo

import requests
import sentry_sdk
from app import util
from app.station import Station
from app.timeline import GraphTimeline
from django.core.cache import cache
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

# Max number of future days, including current day, to retrieve wind forecasts. Open-Meteo supports 16 days.
_max_forecast_days = 14
_request_timeout_seconds = 5
_cache_timeout_seconds = 30 * 60  # 30 min

"""
  Access Wind forecasts from open-meteo.com.
"""
base_url = "https://api.open-meteo.com/v1/forecast"


class WindForecast(TypedDict):
    mph: float
    dir: int


class RawForecast(BaseModel):
    """The parsed/validated "hourly" or "minutely_15" section of the Open-Meteo response.
    pydantic coerces JSON ints and numeric strings into the declared list element types, so
    downstream code can treat these as plain str/float lists."""

    model_config = ConfigDict(frozen=True)
    time: list[str]
    wind_speed_10m: list[float]
    wind_direction_10m: list[int]


def get_wind_forecast(
    station: Station, timeline: GraphTimeline, hilo_mode: bool
) -> dict[datetime, WindForecast]:
    """
    Fetch wind speed and direction forecast for the desired timeline. The data provider currently
    supports 14 days counting the current date. If the timeline contains no times inside that window,
    an empty dict is returned.  Otherwise, the entire 14-day dict is returned, and it's up to the caller
    to use the desired subset of data.  This data is cached for a period of time, initially 30 minutes.
    If the provider has updated their data since the cache was populated, then the data will be up to
    30 minutes stale. This should be acceptable for this type of data, but if not, the cache time can
    be adjusted as necessary.

    Args:
        station (Station): the SWMP station
        timeline (Timeline): the timeline
        hilo_mode: if true, pull 15-min data instead of hourly, so graph will have something to display for every high or low.

    Returns:
        - dict of hourly or 15-min forecasts for the relevant portion of the timeline. {datetime: {"mph": float, "dir": int}}.
    """

    # If the forecast window does not overlap the timeline, there's nothing to do.
    if timeline.is_all_past() or timeline.start_date > timeline.now.date() + timedelta(
        days=_max_forecast_days - 1
    ):
        return {}

    cache_key = "openmeteo-" + ("hilo" if hilo_mode else "15")

    # first try to read it from cache
    data: dict[datetime, WindForecast] = cache.get(cache_key)
    if data:
        logger.debug(f"Cache HIT for {cache_key}")
        return data

    # Not in cache yet, so go to the source.
    try:
        logger.debug(f"Cache MISS for {cache_key}")
        raw_forecast = pull_data(station, hilo_mode)
        data = pred_json_to_dict(raw_forecast, timeline.time_zone)
        if len(data) > 0:
            cache.set(cache_key, data, timeout=_cache_timeout_seconds)
        return data
    except Exception as e:  # noqa
        logger.error(f"Exception: {e}", stack_info=False)
        sentry_sdk.capture_exception(e)
        return {}


@util.request_logger
def pull_data(station: Station, hilo_mode: bool) -> RawForecast:
    # Pull the data and validate the "granularity" section, with keys "time", "wind_speed_10m",
    # and "wind_direction_10m". A malformed payload raises ValidationError.
    granularity = "hourly" if not hilo_mode else "minutely_15"

    params: dict[str, str | int | float] = {
        "latitude": station.weather_location["lat"],
        "longitude": station.weather_location["lng"],
        "timezone": station.time_zone.key,
        granularity: "wind_speed_10m,wind_direction_10m",
        "forecast_days": _max_forecast_days,
    }

    response = requests.get(
        base_url,
        params=params,
        timeout=_request_timeout_seconds,
    )
    response.raise_for_status()
    return RawForecast.model_validate(json.loads(response.text)[granularity])


def pred_json_to_dict(
    pred_json: RawForecast,
    tzone: ZoneInfo | tzinfo,
) -> dict[datetime, WindForecast]:
    result: dict[datetime, WindForecast] = {}
    for t, s, d in zip(
        pred_json.time,
        pred_json.wind_speed_10m,
        pred_json.wind_direction_10m,
    ):
        dt = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=tzone)
        result[dt] = WindForecast(mph=util.kilometers_to_miles(s), dir=d)

    return result
