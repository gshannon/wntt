import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import util
from app.datasource import astrotide, cdmo, surge, syzygy
from app.hilo import Hilo
from app.station import Station
from app.timeline import Timeline

from . import tzutil as tz

logger = logging.getLogger(__name__)


def get_latest_conditions(station: Station) -> dict:
    """
    Pull the most recent wind, tide & temp readings from CDMO, some tide predictions and moon phase data.
    These API calls are done in parallel.
    Args:
        station (Station): the station
    Returns:
        a dict with all the data needed for the latest conditions display.
    """

    # Find recent cdmo data. If it's not in this time window, it's not current enough to display.
    cdmo_end_dt = util.round_to_quarter(tz.now(station.time_zone))
    cdmo_timeline = Timeline(cdmo_end_dt - timedelta(hours=4), cdmo_end_dt)
    water_dict = cdmo.get_water_data(station, cdmo_timeline)
    wind_dict = cdmo.get_wind_data(station, cdmo_timeline)

    # For future tides, we start at 1 minute in future and go far enough out to cover diurnal and semidiurnal.
    future_start_dt = tz.now(station.time_zone)
    future_end_dt = future_start_dt + timedelta(days=1)
    astro_dict = astrotide.get_hilo_astro_tides(
        station.noaa_station_id,
        Timeline(future_start_dt, future_end_dt),
        station.navd88_feet_to_mllw_feet,
        True,
    )
    moon_dict = syzygy.get_current_moon_phases(station.time_zone)
    surge_timeline = Timeline(
        tz.now(station.time_zone), tz.now(station.time_zone) + timedelta(days=1)
    )
    surge_dict = surge.get_future_surge_data(
        surge_timeline, station.noaa_station_id, None
    )

    return extract_data(
        wind_dict,
        water_dict,
        astro_dict,
        surge_dict,
        moon_dict,
        station.time_zone,
    )


def extract_data(
    wind_dict, water_dict, astro_dict, surge_dict, moon_dict, tzone: ZoneInfo = None
) -> dict:
    # Get the most recent 2 tide readings, and compute whether rising or falling. Since these are dense dicts,
    # we don't have to worry about missing data.  All dict keys are in chronological order.
    if len(water_dict) > 0:
        latest_water_dt = max(water_dict)
        latest_vals = water_dict[latest_water_dt]
        latest_tide_val = latest_vals[cdmo.Param.Tide.label]
        tide_str = f"{latest_tide_val:.2f}"
        latest_temp_val = latest_vals[cdmo.Param.Temperature.label]
        temp_str = f"{latest_temp_val:.1f}"
        del water_dict[latest_water_dt]
    else:
        tide_str = latest_water_dt = temp_str = None

    if len(water_dict) > 0:
        prior_tide_dt = max(water_dict)
        prior_tide_val = water_dict[prior_tide_dt][cdmo.Param.Tide.label]
        direction_str = "rising" if prior_tide_val < latest_tide_val else "falling"
    else:
        direction_str = None

    if len(wind_dict) > 0:
        latest_wind_dt, wind_data = max(wind_dict.items(), key=lambda x: x[0])
        wind_speed_str = wind_data[cdmo.Param.WindSpeed.label]
        wind_gust_str = wind_data[cdmo.Param.WindGust.label]
        wind_dir_deg = wind_data[cdmo.Param.WindDir.label]
    else:
        latest_wind_dt = wind_speed_str = wind_gust_str = wind_dir_deg = None

    # Get the time and type of the next high or low tide prediction.
    # dict is already sorted by datetime, so we just need to get the first real_dt that's in the future.
    futures = [
        v
        for v in astro_dict.values()
        if v.real_dt > tz.now(tzone) and v.hilo == Hilo.HIGH
    ]
    if len(futures) > 0:
        next_tide_dt = futures[0].real_dt
        next_tide_str = f"{futures[0].value:.2f}"
        next_tide_type = "H"
    else:
        next_tide_dt = next_tide_type = next_tide_str = None

    surge_str, creation_dt = get_surge_info(surge_dict, next_tide_dt)

    return {
        "wind_speed": wind_speed_str,
        "wind_gust": wind_gust_str,
        "wind_dir_deg": wind_dir_deg,
        "tide": tide_str,
        "tide_dir": direction_str,
        "temp": temp_str,
        "wind_time": latest_wind_dt,
        "tide_time": latest_water_dt,
        "temp_time": latest_water_dt,
        "phase": moon_dict["current"],
        "phase_dt": moon_dict["currentdt"],
        "next_phase": moon_dict["nextphase"],
        "next_phase_dt": moon_dict["nextdt"],
        "next_tide_dt": next_tide_dt,
        "next_tide_str": next_tide_str,
        "next_tide_type": next_tide_type,
        "next_tide_surge_str": surge_str,
        "surge_time": creation_dt,
    }


def get_surge_info(surge_dict, next_tide_dt) -> tuple[str, datetime]:
    # Get the storm surge value associated with the tide time, but only if it's within one hour.
    # Returns estimated surge value as a string, and utc datetime
    surge_str = None
    if next_tide_dt is None or "surges" not in surge_dict:
        logger.warning("Insufficent data to determine surge")
        return surge_str

    best_delta = None
    best_dt_match = None
    best_surge_match = None
    for dt in surge_dict["surges"]:
        delta_secs = abs((dt - next_tide_dt).total_seconds())
        if delta_secs <= 3600 and (best_delta is None or delta_secs < best_delta):
            best_delta = delta_secs
            best_dt_match = dt
            best_surge_match = surge_dict["surges"][dt]

    if best_delta is None:
        logger.debug(f"No surge value was found for tide date {next_tide_dt}")
        return surge_str

    logger.debug(
        f"Storm surge: {best_surge_match}, surge dt {best_dt_match}, tide_dt {next_tide_dt}"
    )
    return f"{best_surge_match:.2f}", datetime.fromisoformat(
        surge_dict["file_creation_utc_iso"]
    )
