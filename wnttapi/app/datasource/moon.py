import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from app.timeline import GraphTimeline
from rest_framework.exceptions import APIException

from . import syzygy_data as data

logger = logging.getLogger(__name__)

# The Navy API requests we use a ID string so they can track usage metrics.
# Example: curl "https://aa.usno.navy.mil/api/moon/phases/date?date=2025-09-29&nump=2"
# base_url = "https://aa.usno.navy.mil/api/moon/phases/date?id=wellsreserve"

utc = ZoneInfo("UTC")

NEW_MOON = "NM"
FIRST_QUARTER = "FQ"
FULL_MOON = "FM"
LAST_QUARTER = "LQ"
PERIGEE = "PG"
APOGEE = "AG"
PERIHELION = "PH"
APHELION = "AH"


def get_current_moon_phases(tzone, asof: datetime = None) -> dict:
    """Get the current moon phase and the next moon phase.

    Args:
        tzone (ZoneInfo): Time zone to return results in.

    Returns:
        dict: {"current": "phase", currentdt: datetime, "nextphase": "phase", "nextdt": datetime}
    """
    # Calculate start date in UTC. To make sure we get both the current phase and next phase, we
    # need to go back 9 days and get 3 phases.
    current_phase_code = None
    current_phase_utc = None
    next_phase_code = None
    next_phase_utc = None

    utc = ZoneInfo("UTC")

    now = asof if asof else datetime.now(tz=tzone)

    now_utc = now.astimezone(utc)

    for utc, code in data.phase_data.items():
        if utc <= now_utc:
            current_phase_code = code
            current_phase_utc = utc
        else:
            next_phase_code = code
            next_phase_utc = utc
            break

    if current_phase_code is None or next_phase_code is None:
        logger.error(f"Could not find current phase. asof={asof}")

    return {
        "current": current_phase_code,
        "currentdt": current_phase_utc.astimezone(tzone),
        "nextphase": next_phase_code,
        "nextdt": next_phase_utc.astimezone(tzone),
    }


def get_syzygy_data(timeline: GraphTimeline) -> dict:
    """Get moon phase, moon perigee and sun perihelion that occur within this timeline, if any.

    Args:
        timeline

    Returns:
        [ { <datetime>: <code> }, ... ]  sorted by datetime
    """
    data = []
    phase_code, phase_dt = get_moon_phase(timeline)
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


def get_moon_phase(timeline: GraphTimeline) -> tuple[str, datetime]:
    """Find the moon phase that is within the timeline, if any.

    Args:
        timeline: we are looking for a phase start within this timeline

    Returns:
        <phase-name>, <phase-datetime>
    """

    for utc, code in data.phase_data.items():
        if timeline.within(utc):
            return code, utc.astimezone(timeline.time_zone)

    return None, None


def get_perigee(timeline: GraphTimeline) -> datetime:
    """Get the datetime of the Perigee that occurs in this timeline, if any."""
    for utc in data.perigee_utc:
        if timeline.within(utc):
            return utc.astimezone(timeline.time_zone)
    return None


def get_perihelion(timeline: GraphTimeline) -> datetime:
    """Get the datetime of the Perihelion that occurs in this timeline, if any."""
    for utc in data.perihelion_utc:
        if timeline.within(utc):
            return utc.astimezone(timeline.time_zone)
    return None


def pull_data(url: str) -> dict:
    """Use this if/when we need to programatically call the API."""
    try:
        response = requests.get(url)
    except Exception as e:
        logger.error(f"Url: {url} Response: {response}", exc_info=e)
        raise APIException()

    if response.status_code != 200:
        logger.error(f"status {response.status_code} calling {url}")
        raise APIException()

    try:
        return json.loads(response.text)

    except ValueError as e:
        logger.error(f"Error calling {url}: {e}")
        raise APIException(e)


def parse_json_year(phase_json: dict, year: int) -> list:
    """Parse the JSON returned by the moon phase API.
    Use this if/when we need to programatically call the API.
    """

    phases = phase_json["phasedata"]
    utc = ZoneInfo("UTC")
    data = []
    start = datetime(year, 1, 1, tzinfo=utc)
    end = datetime(year, 12, 31, 23, 59, tzinfo=utc)

    for entry in phases:
        phase = entry["phase"]
        dt_str = (
            f"{entry['year']}-{entry['month']:02d}-{entry['day']:02d} {entry['time']}"
        )
        dt_utc = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=utc)
        if start <= dt_utc <= end:
            data.append({dt_utc: phase})
    return data
