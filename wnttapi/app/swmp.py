import logging
from datetime import timedelta

from app import util
from app.datasource import astrotide, cdmo, moon
from app.datasource.apiutil import APICall, run_parallel
from app.station import Station
from app.timeline import Timeline

from . import tzutil as tz

logger = logging.getLogger(__name__)


def get_latest_conditions(station: Station) -> dict:
    """
    Pull the most recent wind, tide & temp readings from CDMO.
    We'll build a timeline that covers the last several hours, since for tide data we only need 2, and
    only 1 for the others.  Most of the time, this will result in only 1 day being requested from CDMO.
    For the next high tide prediction, we'll build a separate timeline that goes out 36 hours to cover
    diurnal locales.
    """

    # Find recent cdmo data. If it's not in this time window, it's not current enough to display.
    cdmo_end_dt = util.round_to_quarter(tz.now(station.time_zone))
    cdmo_timeline = Timeline(cdmo_end_dt - timedelta(hours=4), cdmo_end_dt)

    # For future tides, we start at 1 minute in future and go far enough out to cover diurnal and semidiurnal.
    future_start_dt = tz.now(station.time_zone) + timedelta(minutes=1)
    future_astro_timeline = Timeline(
        future_start_dt, future_start_dt + timedelta(hours=36)
    )

    cdmo_calls = [
        APICall("wind", cdmo.get_recorded_wind_data, station, cdmo_timeline),
        APICall("tide", cdmo.get_recorded_tides, station, cdmo_timeline),
        APICall("temp", cdmo.get_recorded_temps, station, cdmo_timeline),
        APICall(
            "next_high_tide", astrotide.get_astro_tides, station, future_astro_timeline
        ),
    ]

    run_parallel(cdmo_calls)

    moon_dict = moon.get_current_moon_phases(station.time_zone)

    return extract_data(
        cdmo_calls[0].data,
        cdmo_calls[1].data,
        cdmo_calls[2].data,
        cdmo_calls[3].data,
        moon_dict,
    )


def extract_data(wind_dict, tide_dict, temp_dict, astro_dicts, moon_dict) -> dict:
    # Get the most recent 2 tide readings, and compute whether rising or falling. Since these are dense dicts,
    # we don't have to worry about missing data.  All dict keys are in chronological order.
    if len(tide_dict) > 0:
        latest_tide_dt, latest_tide_val = max(tide_dict.items(), key=lambda x: x[0])
        tide_str = f"{latest_tide_val:.2f}"
        del tide_dict[latest_tide_dt]
    else:
        tide_str = latest_tide_dt = None

    if len(tide_dict) > 0:
        _, prior_tide_val = max(tide_dict.items(), key=lambda x: x[0])
        direction_str = "rising" if prior_tide_val < latest_tide_val else "falling"
    else:
        direction_str = None

    if len(wind_dict) > 0:
        latest_wind_dt, wind_data = max(wind_dict.items(), key=lambda x: x[0])
        wind_speed_str = wind_data["speed"]
        wind_gust_str = wind_data["gust"]
        wind_dir_str = util.degrees_to_dir(wind_data["dir"])
    else:
        latest_wind_dt = wind_speed_str = wind_gust_str = wind_dir_str = None

    if len(temp_dict) > 0:
        latest_temp_dt, temp = max(temp_dict.items(), key=lambda x: x[0])
        temp_str = f"{util.centigrade_to_fahrenheit(temp):.1f}"
    else:
        latest_temp_dt = temp_str = None

    # These are all from the future. Extract the minimum actual time with type H, which is the next high tide.
    highs = {key: val for key, val in astro_dicts[1].items() if val["type"] == "H"}
    high_dts = list(map(lambda d: d["real_dt"], highs.values()))
    next_high_dt = min(high_dts) if len(high_dts) > 0 else None
    if next_high_dt is None:
        logger.error(f"No future high tide found in astro tide data: {astro_dicts[1]}")

    return {
        "wind_speed": wind_speed_str,
        "wind_gust": wind_gust_str,
        "wind_dir": wind_dir_str,
        "tide": tide_str,
        "tide_dir": direction_str,
        "temp": temp_str,
        "wind_time": latest_wind_dt,
        "tide_time": latest_tide_dt,
        "temp_time": latest_temp_dt,
        "phase": moon_dict["current"],
        "phase_dt": moon_dict["currentdt"],
        "next_phase": moon_dict["nextphase"],
        "next_phase_dt": moon_dict["nextdt"],
        "next_high_tide": next_high_dt,
    }


def ftime(dt):
    return dt.strftime("%b %d %Y %I:%M %p")
