import logging
from datetime import timedelta
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
    obs_tides = cdmo.get_water_data(station, cdmo_timeline)
    winds = cdmo.get_wind_data(station, cdmo_timeline)

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
        winds,
        obs_tides,
        astro_dict,
        surge_dict,
        moon_dict,
        station.time_zone,
    )


def extract_data(
    winds: dict,
    obs_tides: dict,
    astro_dict: dict,
    surge_dict: dict,
    moon_dict: dict,
    tzone: ZoneInfo,
) -> dict:

    data = {
        "phase": moon_dict.get("current", None),
        "phase_dt": moon_dict.get("currentdt", None),
        "next_phase": moon_dict.get("nextphase", None),
        "next_phase_dt": moon_dict.get("nextdt", None),
    }

    if len(winds) > 0:
        latest_wind_dt, wind_rec = max(winds.items(), key=lambda x: x[0])
        data["wind_speed"] = wind_rec.speed_mph
        data["wind_gust"] = wind_rec.gust_mph
        data["wind_dir_deg"] = wind_rec.direction_deg
        data["wind_time"] = latest_wind_dt

    # get the latest water level and temperature readings.
    latest_tide_rec = None
    # convert to list of tuples
    items = sorted(obs_tides.items())
    if len(items) >= 1:
        (latest_tide_dt, latest_tide_rec) = items[-1]
        data["tide"] = latest_tide_rec.corrected_mllw_feet
        data["tide_time"] = latest_tide_dt
        data["temp"] = latest_tide_rec.temp_f

    # to determine whether it's rising or falling, we need the prior tide record.
    if len(items) >= 2:
        (_, prior_tide_rec) = items[-2]
        data["tide_dir"] = (
            "rising"
            if prior_tide_rec.corrected_mllw_feet < latest_tide_rec.corrected_mllw_feet
            else "falling"
        )

    # Get the time and type of the next high tide prediction. The dict is already sorted by datetime key, so we
    # just need to get the first real_dt that's in the future.
    futures = [
        v
        for v in astro_dict.values()
        if v.real_dt > tz.now(tzone) and v.hilo == Hilo.HIGH
    ]

    next_tide_dt = None
    if len(futures) > 0:
        next_tide_dt = futures[0].real_dt
        data["next_tide_dt"] = next_tide_dt
        data["next_high_tide"] = futures[0].value
        data["next_tide_surge"] = find_nearest_surge_value(surge_dict, next_tide_dt)
        data["surge_time"] = surge_dict.get("file_creation_dt", None)

    return data


def find_nearest_surge_value(surge_dict, next_tide_dt) -> float:
    # Get the nearest storm surge value associated with the tide time, past or future,
    # within one hour. Returns estimated surge value, or None if no value is found.
    if next_tide_dt is None or "surges" not in surge_dict:
        logger.warning("Insufficent data to determine surge")
        return None

    best_delta = None
    best_dt_match = None
    best_surge = None
    for dt in surge_dict["surges"]:
        delta_secs = abs((dt - next_tide_dt).total_seconds())
        if delta_secs <= 3600 and (best_delta is None or delta_secs < best_delta):
            best_delta = delta_secs
            best_dt_match = dt
            best_surge = float(surge_dict["surges"][dt])

    if best_delta is None:
        logger.debug(f"No surge value was found for tide date {next_tide_dt}")
        return None

    logger.debug(
        f"Storm surge: {best_surge}, surge dt {best_dt_match}, tide_dt {next_tide_dt}"
    )
    return best_surge
