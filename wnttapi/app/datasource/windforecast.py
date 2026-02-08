import json
import logging
from datetime import datetime, time, timedelta
import sentry_sdk

import requests
from app import tzutil as tz
from app import util as util
from app.station import Station
from app.timeline import GraphTimeline

logger = logging.getLogger(__name__)

# Max number of future days, including current day, to retrieve wind forecasts. Open-Meteo supports 16 days.
max_forecast_days = 14

"""
"""
base_url = (
    "https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&timezone={}"
    "&{}=wind_speed_10m,wind_direction_10m&forecast_days={}"
)


def get_wind_forecast(
    station: Station, timeline: GraphTimeline, hilo_mode: bool
) -> dict:
    """
    Fetch wind speed and direction forecast for the desired timeline. We only support forecasts for a period of 7
    days starting with the current date, so if timeline does not overlap with that time window, no data is retrieved.

    Args:
        station (Station): the SWMP station
        timeline (Timeline): the timeline
        hilo_mode: if true, pull 15-min data instead of hourly, so graph will have something to display for every high or low.

    Returns:
        - dict of hourly or 15-min forecasts for the relevant portion of the timeline. {datetime: {"mph": float, "dir": str}}.
    """

    # If the forecast window does not overlap the timeline, do nothing.
    # max(timeline) must be > min(window) AND max(window) must be > min(timeline)
    now = tz.now(station.time_zone)

    overlap = get_forecast_window(timeline, now)
    if len(overlap) == 0:
        return {}

    days = (overlap[-1].date() - now.date()).days + 1
    forecast_json = pull_data(station, days, hilo_mode)

    if len(forecast_json) > 0:
        return pred_json_to_dict(forecast_json, timeline, overlap, now)
    return {}


def get_forecast_window(timeline: GraphTimeline, now: datetime) -> list:
    """
    Build a list of datetimes which are a subset of the timeline for which we would like
    to get wind speed and direction forecasts.
    """
    if now.tzinfo != timeline.time_zone:
        raise util.InternalError
    max_window_date = now.date() + timedelta(days=max_forecast_days - 1)
    max_window_dt = datetime.combine(max_window_date, time(23, 0)).replace(
        tzinfo=now.tzinfo
    )

    # Determine the part of the forecast window that overlaps the timeline.
    overlap = list(
        filter(
            lambda dt: dt.minute == 0 and now <= dt <= max_window_dt,
            timeline.get_requested(),
        )
    )
    return overlap


def pull_data(station: Station, forecast_days: int, hilo_mode: bool) -> dict:
    granularity = "hourly" if not hilo_mode else "minutely_15"
    url = base_url.format(
        station.weather_station_latitude,
        station.weather_station_longitude,
        station.time_zone.key,
        granularity,
        forecast_days,
    )
    reason = None

    try:
        response = requests.get(url)
        json_dict = json.loads(response.text)
        if response.status_code != 200:
            if json_dict.get("error", False):
                # An error might look like this:
                # {"error":true,"reason":"Forecast days is invalid. Allowed range 0 to 16. Given 16."}
                reason = json_dict.get("reason", "(not given)")
            else:
                reason = "code {response.status_code}"
            raise Exception
        keys = list(json_dict.keys())
        logger.info(keys)
        return json_dict[granularity]

    except Exception as e:
        e.add_note(f"Url: {url}")
        if reason:
            e.add_note(reason)
        logger.exception(str(e))
        sentry_sdk.capture_exception(e)
        return {}


def pred_json_to_dict(
    pred_json: dict, timeline: GraphTimeline, overlap: list, asof: datetime
):
    if overlap[0].tzinfo != timeline.time_zone:
        raise util.InternalError
    result = {}
    try:
        for t, s, d in zip(
            pred_json["time"],
            pred_json["wind_speed_10m"],
            pred_json["wind_direction_10m"],
        ):
            dt = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(
                tzinfo=timeline.time_zone
            )  # '2026-01-13T17:30'

            if dt >= asof:
                if dt > overlap[-1]:
                    break  # we're past the range of interest
                if timeline.contains(dt):
                    result[dt] = {
                        "mph": util.kilometers_to_miles(float(s)),
                        "dir": d,
                        "dir_str": util.degrees_to_dir(int(d)),
                    }

        return result
    except Exception as e:
        logger.exception(str(e))
        sentry_sdk.capture_exception(e)
        return {}
