import csv
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.timeline import GraphTimeline
from django.core.cache import cache

logger = logging.getLogger(__name__)
_default_file_dir = "/data/syzygy"
utc = ZoneInfo("UTC")

NEW_MOON = "NM"
FIRST_QUARTER = "FQ"
FULL_MOON = "FM"
LAST_QUARTER = "LQ"
PERIGEE = "PG"
APOGEE = "AG"
PERIHELION = "PH"
APHELION = "AH"


def get_current_moon_phases(
    tzone, asof: datetime = None, data_dir: str = _default_file_dir
) -> dict:
    """Get the current moon phase and the next moon phase.

    Args:
        tzone (ZoneInfo): Time zone to return results in.
        asof (datetime, optional): For testing. If given, use this datetime as the "now" time.

    Returns:
        dict: {"current": "phase", currentdt: datetime, "nextphase": "phase", "nextdt": datetime}
    """
    current_phase_code = None
    current_phase_utc = None
    next_phase_code = None
    next_phase_utc = None

    utc = ZoneInfo("UTC")

    now = asof if asof else datetime.now(tz=tzone)

    now_utc = now.astimezone(utc)

    data = get_or_load_phase_data(data_dir)

    for utc, code in data.items():
        if utc <= now_utc:
            current_phase_code = code
            current_phase_utc = utc
        else:
            next_phase_code = code
            next_phase_utc = utc
            break

    if current_phase_code is None or next_phase_code is None:
        logger.error(f"Could not find current or next phase asof={asof}")

    return {
        "current": current_phase_code,
        "currentdt": current_phase_utc.astimezone(tzone) if current_phase_utc else None,
        "nextphase": next_phase_code,
        "nextdt": next_phase_utc.astimezone(tzone) if next_phase_utc else None,
    }


def get_syzygy_data(timeline: GraphTimeline, data_dir: str = _default_file_dir) -> dict:
    """Get moon phase, moon perigee and sun perihelion that occur within this timeline,
    sorted by datetime.

    Args:
        timeline

    Returns:
        [ { <datetime>: <code> }, ... ]  sorted by datetime
    """
    data = []
    phase_code, phase_dt = get_moon_phase(timeline, data_dir)
    if phase_dt:
        data.append({"code": phase_code, "dt": phase_dt})
    perigee_dt = get_perigee(timeline)
    if perigee_dt:
        data.append({"code": PERIGEE, "dt": perigee_dt})
    perihelion_dt = get_perihelion(timeline)
    if perihelion_dt:
        data.append({"code": PERIHELION, "dt": perihelion_dt})

    # These must be sorted by time, the graph is depending on it.
    return sorted(data, key=lambda d: d["dt"])


def get_moon_phase(
    timeline: GraphTimeline, data_dir: str = _default_file_dir
) -> tuple[str, datetime]:
    """Find the moon phase that is within the timeline, if any.

    Args:
        timeline: we are looking for a phase start within this timeline

    Returns:
        <phase-name>, <phase-datetime>
    """

    data = get_or_load_phase_data(data_dir)

    for utc, code in data.items():
        if timeline.contains(utc):
            return code, utc.astimezone(timeline.time_zone)
        if utc > timeline.end_dt:
            break

    return None, None


def get_perigee(timeline: GraphTimeline, data_dir: str = _default_file_dir) -> datetime:
    """Get the datetime of the Perigee that occurs in this timeline, if any."""
    data = get_or_load_datetime_data("perigee", data_dir)
    for utc in data:
        if timeline.contains(utc):
            return utc.astimezone(timeline.time_zone)
        if utc > timeline.end_dt:
            break
    return None


def get_perihelion(
    timeline: GraphTimeline, data_dir: str = _default_file_dir
) -> datetime:
    """Get the datetime of the Perihelion that occurs in this timeline, if any."""
    data = get_or_load_datetime_data("perihelion", data_dir)
    for utc in data:
        if timeline.contains(utc):
            return utc.astimezone(timeline.time_zone)
        if utc > timeline.end_dt:
            break
    return None


def get_or_load_datetime_data(type: str, data_dir: str = _default_file_dir) -> list:
    """Get from cache a list of datetimes. Load from disk to cache first if necessary."""
    cache_key = f"{type}_data"
    data = cache.get(cache_key)
    if data is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return data

    data = []
    filepath = f"{data_dir}/{type}.csv"

    with open(filepath, newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                dt_utc = datetime.strptime(row[0], "%Y-%m-%d %H:%M").replace(tzinfo=utc)
                data.append(dt_utc)
            except Exception as e:
                logger.error(f"Bad datetime in {filepath}: {row[0]}", exc_info=e)

    logger.debug(f"Loaded {len(data)} {type} entries from {filepath}")
    cache.set(cache_key, data, timeout=None)  # unlimited timeout
    return data


def get_or_load_phase_data(data_dir: str = _default_file_dir) -> dict:
    """Get from cache a dict of moon phases. Load from disk to cache first if necessary."""
    cache_key = "phase_data"
    data = cache.get(cache_key)
    if data is not None:
        logger.debug(f"Cache hit for {cache_key}")
        return data

    data = {}
    filepath = f"{data_dir}/phases.csv"

    with open(filepath, newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                dt_utc = datetime.strptime(row[0], "%Y-%m-%d %H:%M").replace(tzinfo=utc)
                type = row[1]
                if type not in [NEW_MOON, FIRST_QUARTER, FULL_MOON, LAST_QUARTER]:
                    logger.error(f"Bad type in {filepath} for {dt_utc}: {type}")
                    raise ValueError(f"Bad type: {type}")
                data[dt_utc] = type
            except Exception as e:
                logger.error(f"Bad datetime in {filepath}: {row[0]}", exc_info=e)

    logger.debug(f"Loaded {len(data)} moon phases from {filepath}")
    cache.set(cache_key, data, timeout=None)  # unlimited timeout
    return data
