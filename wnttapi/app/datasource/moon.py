import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

# The Navy API requests we use a ID string so they can track usage metrics.
base_url = "https://aa.usno.navy.mil/api/moon/phases/date?id=wellsreserve"


def get_moon_phases(tzone) -> dict:
    """Get the current moon phase and the next moon phase.

    Args:
        tzone (ZoneInfo): Time zone to return results in.

    Returns:
        dict: {"current": "phase", currentdt: datetime, "nextphase": "phase", "nextdt": datetime}
    """
    # Calculate start date in UTC. To make sure we get both the current phase and next phase, we
    # need to go back 9 days and get 3 phases.
    start_date_utc = datetime.now(tz=tzone).date() - timedelta(days=9)
    url = f"{base_url}&date={start_date_utc.isoformat()}&nump=3"
    logger.debug(f"url: {url}")
    json = pull_data(url)
    phase_dict = parse_json(json, tzone)

    return phase_dict


def pull_data(url: str) -> dict:
    """Call the API and return the moon phase data as a json list of dicts

    Args:
        url (str): _description_

    Raises:
        APIException: If there was an error calling the API

    Returns:
        dict: JSON response from the API
    """
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


def parse_json(phase_json: dict, tzone, asof: datetime = None) -> dict:
    """Parse the JSON returned by the moon phase API.

    Args:
        phase_json (dict): json that looks like this:
            API return looks like this (times in UTC):
    {
        "apiversion": "4.0.1",
        "day": 11,
        "month": 9,
        "numphases": 3,
        "phasedata": [
            {
            "day": 14,
            "month": 9,
            "phase": "Last Quarter",
            "time": "10:33",
            "year": 2025
            },
            {
            "day": 21,
            "month": 9,
            "phase": "New Moon",
            "time": "19:54",
            "year": 2025
            },
            ...
        ]
    }

        tzone: time zone to return datetimes in
        asof (datetime, optional): For testing only. Defaults is current time.

    Returns:
        dict: {"current": "phase", "currentdt": datetime, "nextphase": "phase", "nextdt": datetime}
    """
    current_phase = None
    current_phase_dt = None
    next_phase = None
    next_phase_dt = None
    now = asof if asof else datetime.now(tz=tzone)

    phases = phase_json["phasedata"]

    for entry in phases:
        # Example entry:
        # {
        #     "day": 14,
        #     "month": 9,
        #     "phase": "Last Quarter",
        #     "time": "10:33",
        #     "year": 2025
        # }
        phase = entry["phase"]
        dt_str = (
            f"{entry['year']}-{entry['month']:02d}-{entry['day']:02d} {entry['time']}"
        )
        utc = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(
            tzinfo=ZoneInfo("UTC")
        )
        dt_local = utc.astimezone(tzone)
        if dt_local <= now:
            current_phase = phase
            current_phase_dt = dt_local
        elif current_phase is not None and next_phase is None:
            next_phase = phase
            next_phase_dt = dt_local
            break

    if current_phase is None or next_phase is None:
        logger.error(f"Could not find current phase. asof={asof} phases={phases}")

    return {
        "current": current_phase,
        "currentdt": current_phase_dt,
        "nextphase": next_phase,
        "nextdt": next_phase_dt,
    }
