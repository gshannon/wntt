import logging
from datetime import timedelta

from app import util
from app.datasource import cdmo

from . import tzutil as tz

time_zone = tz.eastern

logger = logging.getLogger(__name__)


def get_latest_info():
    """
    Pull the most recent wind, tide & temp readings from CDMO.
    We'll build a timeline that covers the last several hours, since for tide data we only need 2, and
    only 1 for the others.  Most of the time, this will result in only 1 day being requested from CDMO.
    """

    end_dt = util.round_to_quarter(tz.now(time_zone))
    start_dt = end_dt - timedelta(hours=4)
    timeline = util.build_timeline(start_dt, end_dt)

    wind_data_dict = cdmo.get_recorded_wind_data(
        timeline
    )  # {dt: {speed, gust, dir, dir_str}}
    hist_tide_dict = cdmo.get_recorded_tides(timeline)  # {dt: tide-in-feet-mllw}
    temp_dict = cdmo.get_recorded_temps(timeline)  # {dt: temp-in-celsius}

    # Get the most recent 2 tide readings, and compute whether rising or falling. Since these are dense dicts,
    # we don't have to worry about missing data.  All dict keys are in chronological order.
    latest_tide_dt = max(hist_tide_dict)
    latest_tide_val = hist_tide_dict[latest_tide_dt]
    del hist_tide_dict[latest_tide_dt]
    prior_tide_dt = max(hist_tide_dict)
    prior_tide_val = hist_tide_dict[prior_tide_dt]
    direction = "rising" if prior_tide_val < latest_tide_val else "falling"

    latest_wind_dt = max(wind_data_dict)
    wind_data = wind_data_dict[latest_wind_dt]  # {speed, gust, dir, dir_str}
    latest_temp_dt = max(temp_dict)

    # logger.debug(f"ws: {wind_speed} [{ftime(wind_time)}], tide: {tide} [{ftime(tide_time)}], temp: {temp} [{ftime(temp_time)}]")
    return {
        "wind_speed": wind_data["speed"],
        "wind_gust": wind_data["gust"],
        "wind_dir": util.degrees_to_dir(wind_data["dir"]),
        "tide": f"{latest_tide_val:.2f}",
        "tide_dir": direction,
        "temp": f"{util.centigrade_to_fahrenheit(temp_dict[latest_temp_dt]):.1f}",
        "wind_time": ftime(latest_wind_dt),
        "tide_time": ftime(latest_tide_dt),
        "temp_time": ftime(latest_temp_dt),
    }


def ftime(dt):
    return dt.strftime("%b %d %Y %I:%M %p")
