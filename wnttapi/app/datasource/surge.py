import csv
import logging
import os
import os.path
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo
from django.core.cache import cache
from rest_framework.exceptions import APIException

from app import tzutil as tz
from app.timeline import Timeline

# /surgedata is a mount defined in docker-compose.yml
# TODO: make surge file reserve specific! Add reserve id to filename, and code logic.
_surge_file_path = "/surgedata/surge-data.csv"
_max_surge = 20
_min_surge = -20

logger = logging.getLogger(__name__)


def get_future_surge_data(timeline: Timeline, last_recorded_dt: datetime) -> dict:
    """Get a dense dict of future storm surge data for all possible timeline datetimes which are past the
    last_recorded_dt param, if given, else the current system time. These are extracted from a csv file
    obtained from NOAA's NOMADS division (nomads.ncep.noaa.gov).  We only have about 4 days of it, so
    don't bother looking too far ahead. We restrict to data past the last recorded data time, if any.

    Args:
        timeline (Timeline): the timeline
        last_recorded_dt (datetime): time of latest recorded tide, or None

    Returns:
        dict: {dt: height MLLW feet} latest predicted surge value for each time in timeline
    """
    future_surge_dict = {}  # {dt: surge_value}

    # Don't bother looking for data more than 6 days in the future.
    if timeline.end_dt >= timeline.now and timeline.start_dt < timeline.now + timedelta(
        days=6
    ):
        future_surge_dict = get_or_load_projected_surge_file(timeline.time_zone)
        # If there's any recorded tides in the timeline, we don't want any data for those times.
        if last_recorded_dt is not None:
            future_surge_dict = {
                dt: val
                for dt, val in future_surge_dict.items()
                if dt > last_recorded_dt
            }

    return future_surge_dict


def calculate_past_storm_surge(astro_dict: dict, obs_dict: dict) -> dict:
    """Calculate the past storm surge, which is the difference between the observed tide and the
    predicted astronomical tide.  This is done for all datetimes in the timeline, and returned as a dict.
    The dict keys are the timeline datetimes, and the values are the calculated storm surge values.
    """
    past_surge = {}  # {dt: surge_value}
    for dt in list(obs_dict.keys()):
        if dt in astro_dict:
            past_surge[dt] = round(obs_dict[dt] - astro_dict[dt], 2)
    return past_surge


def get_or_load_projected_surge_file(
    timezone: ZoneInfo, surge_file_path=_surge_file_path
) -> dict:
    """
    The csv file containing the projected surge data is updated on the NOAA site every 6 hours,
    and is normally downloaded by a cron job. Once loaded, its contents are cached in Django for performance.
    So here, we have to determine if the disk file has been replaced since we last processed it. Therefore,
    if the data file exists and has not been replaced by a newer file, read the cache. Otherwise, read the
    download file, throwing out all but xx:00 and xx:30 -- since the data is in 6-minute intervals
    and we show 15-min intervals. Then save that to cache and return it. We read the entire file, even data
    from the past, so graphs can display this data for past times when observed data is missing.

    If file is missing, unreadable, or corrupt, an error is logged an an empty dict is returned.
    All datetimes in the file are in UTC, and are converted as requested timezone.

    Args:
        timezone (ZoneInfo): Timezone to convert to.
        surge_file_path (str, optional): for testing, use to override standard surge file location.

    Raises:
        APIException: if file cannot be opened

    Returns:
        dict: key = datetime, value = surge value in feet relative to MLLW
    """

    # Since this is a small cache (< 1Kb), we'll use the process ID as the cache key, so each worker can have its own copy.
    # This should avoid any multi-threading issues when setting the cache with multiple workers.
    pid = os.getpid()
    # The cached data is a dict with keys 'id' and 'data'.  'id' is the file's mtime, 'data' is the surge data.
    cached = cache.get(pid)
    logger.debug(f"found surge cache for process {pid}? {cached is not None}")
    if cached is not None:
        logger.debug(f"cached id: {cached['id']}")

    file_id = (
        os.path.getmtime(_surge_file_path)
        if os.path.isfile(_surge_file_path) and os.access(_surge_file_path, os.R_OK)
        else None
    )
    logger.debug(f"current file id: {file_id}")
    if file_id is None:
        if cached is None:
            logger.error(
                f"{_surge_file_path} is not found, and there is no cached surge data!"
            )
            return {}
        else:
            logger.error(f"Can't read {_surge_file_path} file, will use cache for now.")
            return cached["data"]

    # So now we know the file exists and is readable.  If we have cached data, check if the file has been updated.
    if cached is not None and file_id == cached["id"]:
        logger.debug(
            f"cache id match id={file_id} {min(cached['data'])} - {max(cached['data'])} "
        )
        return cached["data"]  # return the cached data

    logger.debug(f"will cache/re-cache surge data, file id = {file_id}")

    surge_data = {}  # key=datetime, value=surge
    logger.debug(f"Reading {_surge_file_path}")
    try:
        """
        Sample data:
                TIME,    TIDE,      OB,   SURGE,    BIAS,      TWL
        202502181200,   2.275,9999.000,  -1.600,9999.000,   0.675
        202502181206,   2.119,9999.000,9999.000,9999.000,9999.000
        202502181212,   1.970,9999.000,9999.000,9999.000,9999.000
        202502181218,   1.829,9999.000,9999.000,9999.000,9999.000
        202502181224,   1.695,9999.000,9999.000,9999.000,9999.000
        202502181230,   1.570,9999.000,9999.000,9999.000,9999.000
        ...
        """
        with open(_surge_file_path) as surge_file:
            reader = csv.reader(surge_file, skipinitialspace=True)
            next(reader)  # skip header row
            for row in reader:
                # Surge values for Wells data is on the hour only, but the data file has a row for every 6 min.
                # Only the times that are multiples of 100 have actual surge data.
                if int(row[0]) % 100 != 0:
                    continue
                # All file datetimes are UTC. Convert to requested tz.
                in_utc = datetime.strptime(row[0], "%Y%m%d%H%M").replace(tzinfo=tz.utc)
                local_dt = in_utc.astimezone(timezone)
                try:
                    surge = float(row[3])
                    if _min_surge <= surge <= _max_surge:
                        surge_data[local_dt] = round(surge, 2)
                    else:
                        logger.error(
                            f"Found unexpected surge value [{surge}] for target {in_utc}"
                        )
                except ValueError:
                    logger.error(f"Invalid surge value: '{row[3]}'")
    except FileNotFoundError:
        logger.error(f"Prediction file not found: {_surge_file_path}")
        return {}

    cache.set(
        pid, {"id": file_id, "data": surge_data}, timeout=60 * 60 * 6
    )  # 6 hour TTL
    logger.debug(
        f"Cached for worker {pid}, {len(surge_data)} values from {_surge_file_path}"
    )
    logger.debug(f"read surge from file {min(surge_data)} - {max(surge_data)} ")
    return surge_data
