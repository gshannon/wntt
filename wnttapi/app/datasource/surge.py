import csv
import logging
import os
import os.path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app import tzutil as tz
from app.timeline import Timeline
from django.core.cache import cache
import sentry_sdk

# /surgedata is a mount defined in docker-compose.yml
_default_surge_file_dir = "/data/surge/data"
_max_surge = 20
_min_surge = -20

logger = logging.getLogger(__name__)


def get_future_surge_data(
    timeline: Timeline, noaa_station_id: str, last_recorded_dt: datetime
) -> dict:
    """Get a dense dict of future storm surge data for all possible timeline datetimes which are past the
    last_recorded_dt param, if given, else the current system time. These are extracted from a csv file
    obtained from NOAA's NOMADS division (nomads.ncep.noaa.gov).  We only have about 4 days of it, so
    don't bother looking too far ahead. We restrict to data past the last recorded data time, if any.

    Args:
        timeline (Timeline): the timeline
        noaa_station_id: the NOAA station code so we can get the right data
        last_recorded_dt (datetime): time of latest recorded tide, or None

    Returns:
        dict: {dt: height MLLW feet} latest predicted surge value for each time in timeline
    """
    future_surge_dict = {}  # {dt: surge_value}

    # Don't bother looking for data more than 6 days in the future.
    if timeline.end_dt >= timeline.now and timeline.start_dt < timeline.now + timedelta(
        days=6
    ):
        future_surge_dict = get_or_load_projected_surge_file(
            noaa_station_id, timeline.time_zone
        )
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
    noaa_station_id: str, timezone: ZoneInfo, surge_file_dir=_default_surge_file_dir
) -> dict:
    """
    The csv files containing projected surge data are updated on the NOAA site every 6 hours,
    and are normally downloaded by a cron job. Once loaded, contents are cached in Django for performance.
    This cache is shared by all workers. Here we determine if the file for the station in question has been
    replaced since it was cached, and update the cache if so. When parsing the file, we throw out all but
    xx:00 and xx:30 since the data is in 6-minute intervals and we show 15-min intervals.

    If file is missing, unreadable, or corrupt, an error is logged and an empty dict is returned.
    All datetimes in the file are in UTC, and are converted as requested timezone.

    Cache structure:
    { <station-id> : [ <file-id>, {data} ] }

    Args:
        noaa_station_id: the NOAA station id, so we know which file to read
        timezone (ZoneInfo): Timezone to convert to.
        surge_file_dir (str, optional): for testing, use to override standard surge file location.

    Returns:
        dict: key = datetime, value = surge value in MLLW feet
    """

    # The cached data is a dict with key=(station_id,mtime) and value=data.
    filepath = f"{surge_file_dir}/{noaa_station_id}.csv"
    file_mtime = (
        os.path.getmtime(filepath)
        if os.path.isfile(filepath) and os.access(filepath, os.R_OK)
        else None
    )
    [saved_mtime, data] = cache.get(noaa_station_id, [None, None])
    logger.debug(f"current mtime: {file_mtime}, saved mtime: {saved_mtime}")

    # First handle the case of a missing file.
    if file_mtime is None:
        sentry_sdk.capture_message(f"missing surge file {filepath}")
        if data is None:
            logger.error(
                "%s is not found, and there is no cached surge data for %s",
                filepath,
                noaa_station_id,
            )
            return {}
        logger.error(f"Can't read {filepath} file, forced to use cache")
        return data

    # So now we know the file exists and is readable.  If we have cached data, check if the file has been updated.
    if data is not None and file_mtime == saved_mtime:
        logger.debug(f"cache id match id={file_mtime} {min(data)} - {max(data)} ")
        return data

    logger.debug(f"will cache/re-cache surge data, file mtime = {file_mtime}")

    data = {}  # key=datetime, value=surge
    logger.debug(f"Reading {filepath}...")
    try:
        """
        Surge files contain a data entry for every 6 minutes, but only the ones with a SURGE value < 9999
        are real. Those line up with top of the hour so we skip every TIME that's not a multiple of 100.
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
        with open(filepath) as surge_file:
            error_cnt = 0
            reader = csv.reader(surge_file, skipinitialspace=True)
            next(reader)  # skip header row
            for row in reader:
                # Only the times that are multiples of 100 have actual surge data.
                if int(row[0]) % 100 != 0:
                    continue
                # All file datetimes are UTC. Convert to requested tz.
                in_utc = datetime.strptime(row[0], "%Y%m%d%H%M").replace(tzinfo=tz.utc)
                local_dt = in_utc.astimezone(timezone)
                try:
                    surge = float(row[3])
                    if _min_surge <= surge <= _max_surge:
                        data[local_dt] = round(surge, 2)
                    else:
                        error_cnt += 1
                        logger.error(
                            f"Found unexpected surge value [{surge}] for target {in_utc}"
                        )
                except ValueError:
                    error_cnt += 1
                    logger.error("Invalid surge value: '%s'", row[3])
            if error_cnt > 0:
                sentry_sdk.capture_message(
                    f"Found {error_cnt} data errors in surge file!"
                )
    except FileNotFoundError:
        msg = f"Prediction file could not be opened: {surge_file}"
        logger.error(msg)
        sentry_sdk.capture_message(msg)
        return {}

    # Cache the data. We'll use a TTL of 24 hours to handle cases where download fails a few times.
    cache.set(noaa_station_id, [file_mtime, data], timeout=60 * 60 * 24)
    logger.debug(
        f"{noaa_station_id}: cached {len(data)} recs from {filepath}, from {min(data)} to {max(data)}"
    )
    return data
