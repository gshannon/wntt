import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from app import util
from app.datasource import astrotide, cdmo, surge, syzygy
from app.datasource.tides import Tide
from app.datasource.winds import Wind
from app.hilo import Hilo, PredictedHighOrLow
from app.station import Station
from app.timeline import Timeline

logger = logging.getLogger(__name__)


class ConditionsData(BaseModel):
    phase: str | None
    phase_dt: datetime | None
    next_phase: str | None
    next_phase_dt: datetime | None
    wind_speed: float | None
    wind_gust: float | None
    wind_dir_deg: int | None
    wind_time: datetime | None
    tide: float | None
    tide_time: datetime | None
    tide_dir: str | None
    temp: float | None
    next_tide_dt: datetime | None
    next_high_tide: float | None
    next_tide_surge: float | None
    surge_time: datetime | None


def get_latest_conditions(station: Station) -> ConditionsData:
    """
    Pull the most recent wind, tide & temp readings from CDMO, some tide predictions and moon phase data.
    These API calls are done in parallel.
    Args:
        station (Station): the station
    Returns:
        a dict with all the data needed for the latest conditions display.
    """

    # Find recent cdmo data. If it's not in this time window, it's not current enough to display.
    cdmo_end_dt = util.round_to_quarter(datetime.now(station.time_zone))
    cdmo_timeline = Timeline(cdmo_end_dt - timedelta(hours=4), cdmo_end_dt)
    obs_tides = cdmo.get_water_data(station, cdmo_timeline)
    winds = cdmo.get_wind_data(station, cdmo_timeline)

    # For future tides, we start at 1 minute in future and go far enough out to cover diurnal and semidiurnal.
    future_start_dt = datetime.now(station.time_zone)
    future_end_dt = future_start_dt + timedelta(days=1)
    astro_dict = astrotide.get_hilo_astro_tides(
        station.noaa_station_id,
        Timeline(future_start_dt, future_end_dt),
        station.navd88_feet_to_mllw_feet,
        True,
    )
    moon_dict = syzygy.get_current_moon_phases(station.time_zone)
    surge_timeline = Timeline(
        datetime.now(station.time_zone),
        datetime.now(station.time_zone) + timedelta(days=1),
    )
    surge_data = surge.get_future_surge_data(surge_timeline, station.noaa_station_id)

    as_dict: dict[str, Any] = extract_data(
        winds,
        obs_tides,
        astro_dict,
        surge_data,
        moon_dict,
        station.time_zone,
    )

    return ConditionsData.model_validate(as_dict)


def extract_data(
    winds: dict[datetime, Wind],
    obs_tides: dict[datetime, Tide],
    astro_dict: dict[datetime, PredictedHighOrLow],
    surge_data: surge.SurgeFileCache | None,
    moon_dict: dict[str, Any],
    tzone: ZoneInfo,
) -> dict[str, Any]:

    data = {
        "phase": moon_dict.get("current"),
        "phase_dt": moon_dict.get("currentdt"),
        "next_phase": moon_dict.get("nextphase"),
        "next_phase_dt": moon_dict.get("nextdt"),
    }

    if len(winds) > 0:
        latest_wind_dt, wind_rec = max(winds.items(), key=lambda x: x[0])
        data["wind_speed"] = wind_rec.speed_mph
        data["wind_gust"] = wind_rec.gust_mph
        data["wind_dir_deg"] = wind_rec.direction_deg
        data["wind_time"] = latest_wind_dt
    else:
        data["wind_speed"] = None
        data["wind_gust"] = None
        data["wind_dir_deg"] = None
        data["wind_time"] = None

    # get the latest water level and temperature readings.
    # convert to list of tuples
    items = sorted(obs_tides.items())
    if len(items) >= 1:
        (latest_tide_dt, latest_tide_rec) = items[-1]
        data["tide"] = latest_tide_rec.corrected_mllw_feet
        data["tide_time"] = latest_tide_dt
        data["temp"] = latest_tide_rec.temp_f
    else:
        data["tide"] = None
        data["tide_time"] = None
        data["temp"] = None

    # to determine whether it's rising or falling, we need the prior tide record.
    if len(items) >= 2:
        (_, prior_tide_rec) = items[-2]
        data["tide_dir"] = (
            "rising"
            if prior_tide_rec.corrected_mllw_feet < latest_tide_rec.corrected_mllw_feet
            else "falling"
        )
    else:
        data["tide_dir"] = None

    # Get the time and type of the next high tide prediction. The dict is already sorted by datetime key, so we
    # just need to get the first real_dt that's in the future.
    futures = [
        v
        for v in astro_dict.values()
        if v.real_dt > datetime.now(tzone) and v.hilo == Hilo.HIGH
    ]

    next_tide_dt = None
    if len(futures) > 0:
        next_tide_dt = futures[0].real_dt
        data["next_tide_dt"] = next_tide_dt
        data["next_high_tide"] = futures[0].value
        data["next_tide_surge"] = find_nearest_surge_value(surge_data, next_tide_dt)
        data["surge_time"] = surge_data.created_at if surge_data else None
    else:
        data["next_tide_dt"] = None
        data["next_high_tide"] = None
        data["next_tide_surge"] = None
        data["surge_time"] = None

    return data


def find_nearest_surge_value(
    surge_data: surge.SurgeFileCache | None, next_tide_dt: datetime
) -> float | None:
    # Get the nearest storm surge value associated with the tide time, past or future,
    # within one hour. Returns estimated surge value, or None if no value is found.
    if next_tide_dt is None or surge_data is None:
        logger.warning("Insufficent data to determine surge")
        return None

    best_delta = None
    best_dt_match = None
    best_surge = None
    for dt, val in surge_data.surges.items():
        delta_secs = abs((dt - next_tide_dt).total_seconds())
        if delta_secs <= 3600 and (best_delta is None or delta_secs < best_delta):
            best_delta = delta_secs
            best_dt_match = dt
            best_surge = val

    logger.debug(
        f"Storm surge: {best_surge}, surge dt {best_dt_match}, tide_dt {next_tide_dt}"
    )
    return best_surge
