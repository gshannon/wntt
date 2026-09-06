import json
import logging
from datetime import datetime, time, timedelta
from typing import TypedDict

import requests
import sentry_sdk
from pydantic import BaseModel

from app import util
from app.station import Station
from app.timeline import GraphTimeline

logger = logging.getLogger(__name__)

# Max number of future days, including current day, to retrieve wind forecasts. Open-Meteo supports 16 days.
_max_forecast_days = 14
_request_timeout_seconds = 5

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

    time: list[str]
    wind_speed_10m: list[float]
    wind_direction_10m: list[int]


def get_wind_forecast(
    station: Station, timeline: GraphTimeline, hilo_mode: bool
) -> dict[datetime, WindForecast]:
    """
    Fetch wind speed and direction forecast for the desired timeline. We only support forecasts for a period of 7
    days starting with the current date, so if timeline does not overlap with that time window, no data is retrieved.

    Args:
        station (Station): the SWMP station
        timeline (Timeline): the timeline
        hilo_mode: if true, pull 15-min data instead of hourly, so graph will have something to display for every high or low.

    Returns:
        - dict of hourly or 15-min forecasts for the relevant portion of the timeline. {datetime: {"mph": float, "dir": int}}.
    """

    # If timeline is in past, or the forecast window does not overlap the timeline, do nothing.
    if timeline.is_all_past():
        return {}

    overlap = get_forecast_window(timeline)
    if len(overlap) == 0:
        return {}

    days = (overlap[-1].date() - timeline.now.date()).days + 1
    forecast = pull_data(station, days, hilo_mode)

    if forecast is None or len(forecast.time) == 0:
        return {}
    return pred_json_to_dict(forecast, timeline, overlap)


def get_forecast_window(timeline: GraphTimeline) -> list[datetime]:
    """
    Build a list of datetimes which are a subset of the timeline for which we would like
    to get wind speed and direction forecasts.
    """
    max_window_date = timeline.now.date() + timedelta(days=_max_forecast_days - 1)
    max_window_dt = datetime.combine(max_window_date, time(23, 0)).replace(
        tzinfo=timeline.time_zone
    )

    # Determine the part of the forecast window that overlaps the timeline.
    overlap = list(
        filter(
            lambda dt: dt.minute == 0 and timeline.now <= dt <= max_window_dt,
            timeline.get_requested(),
        )
    )
    return overlap


@util.request_logger
def pull_data(
    station: Station, forecast_days: int, hilo_mode: bool
) -> RawForecast | None:
    granularity = "hourly" if not hilo_mode else "minutely_15"

    params: dict[str, str | int | float] = {
        "latitude": station.weather_station_latitude,
        "longitude": station.weather_station_longitude,
        "timezone": station.time_zone.key,
        granularity: "wind_speed_10m,wind_direction_10m",
        "forecast_days": forecast_days,
    }

    response = requests.get(
        base_url,
        params=params,
        timeout=_request_timeout_seconds,
    )
    response.raise_for_status()
    # Validate the "granularity" section (keys "time", "wind_speed_10m", "wind_direction_10m").
    # A malformed payload raises ValidationError, which request_logger turns into None.
    return RawForecast.model_validate(json.loads(response.text)[granularity])


def pred_json_to_dict(
    pred_json: RawForecast,
    timeline: GraphTimeline,
    overlap: list[datetime],
) -> dict[datetime, WindForecast]:
    if overlap[0].tzinfo != timeline.time_zone:
        raise util.InternalError("incompatible timezones")
    result: dict[datetime, WindForecast] = {}
    try:
        for t, s, d in zip(
            pred_json.time,
            pred_json.wind_speed_10m,
            pred_json.wind_direction_10m,
        ):
            dt = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(
                tzinfo=timeline.time_zone
            )  # '2026-01-13T17:30'

            if dt >= timeline.now:
                if dt > overlap[-1]:
                    break  # we're past the range of interest
                if timeline.contains(dt):
                    result[dt] = WindForecast(mph=util.kilometers_to_miles(s), dir=d)

        return result
    except Exception as e:
        logger.exception(str(e))
        sentry_sdk.capture_exception(e)
        return {}
