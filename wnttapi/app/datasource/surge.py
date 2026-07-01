import csv
import logging
import os
import os.path
import re
from datetime import datetime, timedelta

import sentry_sdk
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

from app import tzutil as tz
from app.timeline import Timeline

from ..models import Surge, SurgeBias
from .cdmo import Param

# /surgedata is a mount defined in docker-compose.yml
_default_surge_file_dir = "/data/surge/data"
_max_surge = 20
_min_surge = -20
_no_value = "9999.000"

logger = logging.getLogger(__name__)


def get_future_surge_data(
    timeline: Timeline,
    noaa_station_id: str,
    last_recorded_dt: datetime,
    surge_file_dir=_default_surge_file_dir,
) -> dict:
    """Get a dense dict of future storm surge data for all possible timeline datetimes. These are
    extracted from a csv file obtained from NOAA's NOMADS division (nomads.ncep.noaa.gov).  They only
    publish about 4 days of it, so don't bother looking too far ahead. We restrict to data later than
    the last_recorded_dt, if provided. This allows callers to use this data for parts of the timeline
    that are in the past, but have no observed tide data to display.

    Args:
        timeline (Timeline): the timeline
        noaa_station_id: the NOAA station code so we can get the right data
        last_recorded_dt (datetime): time of latest recorded tide, or None

    Returns:
    {
        "filedate": filedate string,
        "cycle": cycle int,
        "file_creation_dt": file download datetime,
        "surges": { <dt>: <surge> }
        "bias1": calc_bias1,
        "bias2": calc_bias2,
        "bias3": calc_bias3,
    }
    """
    future_surge_dict = {}
    # Don't bother looking for data more than 6 days in the future.
    if timeline.end_dt >= timeline.now and timeline.start_dt < timeline.now + timedelta(
        days=6
    ):
        future_surge_dict = get_or_load_projected_surge_file(
            noaa_station_id, timeline, surge_file_dir
        )
        # If there's any recorded tides in the timeline, we don't want any data for those times.
        if last_recorded_dt is not None and len(future_surge_dict) > 0:
            future_surge_dict["surges"] = {
                dt: val
                for dt, val in future_surge_dict["surges"].items()
                if dt > last_recorded_dt
            }

    return future_surge_dict


def get_past_storm_surge(astro_dict: dict, water_dict: dict) -> dict:
    """Calculate the past storm surge, which is the difference between the observed tide and the
    predicted tide.

    Args:
        astro_dict (dict): predicted tide values, in MLLW feet, keyed by datetime
        water_dict (dict): observed tide values, in MLLW feet, keyed by datetime

    Returns:
        dict: A dictionary of past storm surge values, keyed by datetime
    """
    data = {}  # {dt: surge_value}
    for dt in water_dict.keys():
        if dt in astro_dict:
            data[dt] = round(water_dict[dt][Param.Tide.label] - astro_dict[dt], 2)
    return data


def get_or_load_projected_surge_file(
    noaa_station_id: str,
    timeline: Timeline,
    surge_file_dir=_default_surge_file_dir,
) -> dict:
    """
    The csv files containing projected surge data are updated on the NOAA web site every 6 hours,
    and are normally downloaded by a cron job. Here, we cached the contents in Django for performance.
    This cache is shared by all workers. When parsing the file, we throw out all but
    xx:00 since only the data at the top of each hour is valid in the files.

    We do not load any data whose tide time is more than 2 hours older than the current time, as that data
    cannot possibly be displayed in the application, and it would serve no purpose to cache it.

    If the latest data for the station is already in cache, we return that. Otherwise, we look for the latest
    file for that station in the surge file directory, parse it and cache the data. We also look in the database
    for a calculated bias value for that station, filedate and cycle, and if found, we return that as well so
    users of this data can add it to the surge values if they want.  We don't do that here in order to enable
    A/B testing of using this calculated bias or not.

    Args:
        noaa_station_id: the NOAA station id, so we know which file to read
        timeline (Timeline): The timeline for which to calculate surge values.
        surge_file_dir (str, optional): for testing, use to override standard surge file location.

    Returns: an object with
        "filedate": filedate string,
        "cycle": cycle int,
        "file_creation_dt": file download datetime,
        "surges": { <dt>: <surge> }
        "bias1": calc_bias1,
        "bias2": calc_bias2,
        "bias3": calc_bias3,
    """
    logger.debug(f"looking in surge cache for station {noaa_station_id}...")

    # pull the existing cache value, if any
    entry = cache.get(noaa_station_id)
    if entry is not None:
        logger.debug(
            f"cache exists for {noaa_station_id} filedate {entry.get('filedate', None)}, cycle {entry.get('cycle', None)}"
        )
    else:
        logger.debug("nothing in cache")

    filepath, filedate, cycle, file_creation_dt = get_latest_file_info(
        noaa_station_id, surge_file_dir
    )

    # First handle the case of a missing file.
    if filedate is None:
        sentry_sdk.capture_message(f"missing surge file for {noaa_station_id}")
        if entry is None:
            logger.error(
                "file not found, and there is no cached surge data for %s",
                noaa_station_id,
            )
            return {}
        logger.error(f"No file for {noaa_station_id}, forced to use cache")
        return entry

    # We have a file. If we also have a cache entry, return the cache if the file isn't newer.
    if entry is not None:
        if filedate == entry.get("filedate") and cycle == entry.get("cycle"):
            logger.debug(
                f"cache match: {noaa_station_id}, {filedate}/{cycle} {min(entry['surges'])} - {max(entry['surges'])} "
            )
            return entry
        else:
            # There's a newer file for this cached station. We'll be replacing with a new one..
            logger.debug(
                f"Will replace old cache for {noaa_station_id}, {filedate}/{cycle}"
            )

    # We have a file, and we need to read it and cache it.
    (calc_bias1, calc_bias2, calc_bias3) = get_calculate_biases(
        noaa_station_id, filedate, cycle
    )

    surges_dict = parse_surge_file(timeline, filepath)
    if len(surges_dict) == 0:
        logger.error(f"No valid surge data found in file {filepath}!")
        sentry_sdk.capture_message(f"No valid surge data found in file {filepath}!")
        return {}

    # Build the payload, cache it & return it.
    payload = {
        "filedate": filedate,
        "cycle": cycle,
        "file_creation_dt": file_creation_dt,
        "surges": surges_dict,
        "bias1": calc_bias1,
        "bias2": calc_bias2,
        "bias3": calc_bias3,
    }
    # We'll use a TTL of 48 hours to handle cases where download fails a few times.
    cache.set(noaa_station_id, payload, timeout=60 * 60 * 48)
    logger.debug(
        f"{noaa_station_id}: cached {len(surges_dict)} surge values, from {min(surges_dict)} to {max(surges_dict)}"
    )
    return payload


def get_latest_file_info(noaa_station_id: str, dir_path: str = _default_surge_file_dir):
    """Find the most recent surge file available for this noaa station. Normally there will be
    just one file for the station, but in case there are more, we sort by name in reverse order
    and take the first one.  The file name format is <noaa_station_id>-<filedate>-<cycle>.csv,
    e.g  8419317-20260213-06.csv.  There are 4 6-hour cycles per day (00, 06, 12, 18).

    Args:
        noaa_station_id: the NOAA station id whose predictions we want
        dir_path (optional): Path of directory to search.  Overrideable for testing.

    Returns:
        str: complete path of the file, or None if not found
        str: filedate string in YYYYMMDD format, or None if not found
        int: the cycle -- 0, 6, 12, or 18, or None if not found
        datetime: datetime in UTC of when the file was created (downloaded), or None if not found
    """
    pattern = r"(\d+)-(\d+)-(\d\d).csv$"  # e.g. 8419317-20260213-06.csv
    filepath, filedate, cycle = None, None, None

    # Sort DirEntry objects by name in reverse (Z-A) order
    for e in sorted(os.scandir(dir_path), key=lambda e: e.name, reverse=True):
        matches = re.findall(
            pattern, e.name
        )  # returns list of tuples, not None if no match
        if len(matches) == 1 and matches[0][0] == noaa_station_id:
            filedate, cycle = (
                matches[0][1],
                int(matches[0][2]),
            )
            filepath = os.path.join(dir_path, e.name)
            file_creation_dt = datetime.fromtimestamp(
                os.path.getctime(filepath), tz=tz.utc
            )
            break

    logger.debug(
        f"surge file for station {noaa_station_id}: {filepath}, filedate {filedate}, cycle {cycle}"
    )
    return filepath, filedate, cycle, file_creation_dt


def get_calculate_biases(noaa_station_id: str, filedate: str, cycle: int):
    """Retrieve calculated biases for a station that doesn't have bias (corrections), like Wells.
    This is experimental, and is not used in the application.  It is intended for A/B testing
    of the calculated bias logic.

    Args:
        noaa_station_id (str): NOAA station id
        filedate (str): surge file date in YYYYMMDD format
        cycle (int): surge file cycle

    Returns:
        tuple: A tuple containing the three calculated biases (calc_bias1, calc_bias2, calc_bias3)
    """
    (calc_bias1, calc_bias2, calc_bias3) = (None, None, None)
    try:
        rec = SurgeBias.objects.get(
            noaa_id=noaa_station_id, filedate=filedate, cycle=cycle
        )
        (calc_bias1, calc_bias2, calc_bias3) = (rec.bias, rec.bias2, rec.bias3)
        logger.debug(
            f"got bias id {rec.id}: {rec.bias} from db for {noaa_station_id} {filedate} cycle {cycle}"
        )
    except ObjectDoesNotExist:
        logger.debug(
            f"Bias record not found in db for {noaa_station_id} {filedate} cycle {cycle}."
        )
    except Exception as exc:
        # Log but do not raise
        logger.exception("Could not read history surge records from db")
        sentry_sdk.capture_exception(exc)

    return calc_bias1, calc_bias2, calc_bias3


def parse_surge_file(timeline: Timeline, filepath: str) -> dict:
    """
    Parse the surge file and return a dict of surge values for all times in the timeline.
    The dict keys are the datetimes and the values are the surge values.
    """
    surges_dict = {}  # key=datetime, value=surge
    logger.debug(f"Reading {filepath}...")
    try:
        """
                TIME,    TIDE,      OB,   SURGE,    BIAS,      TWL
        202502181200,   2.275,9999.000,  -1.600,9999.000,   0.675
        ...
        """
        cutoff = timeline.now - timedelta(hours=2)
        with open(filepath) as surge_file:
            error_cnt = 0
            reader = csv.reader(surge_file, skipinitialspace=True)
            next(reader)  # skip header row
            for row in reader:
                date_str, surge_str, bias_str = row[0], row[3], row[4]

                # Only the times that are multiples of 100 have actual surge data.
                if int(date_str) % 100 != 0:
                    continue
                # All file datetimes are UTC. Convert to requested tz.
                in_utc = datetime.strptime(date_str, "%Y%m%d%H%M").replace(
                    tzinfo=tz.utc
                )
                local_dt = in_utc.astimezone(timeline.time_zone)
                if local_dt < cutoff:
                    continue
                try:
                    surge = float(surge_str) + (
                        float(bias_str) if bias_str != _no_value else 0
                    )
                    if _min_surge <= surge <= _max_surge:
                        surges_dict[local_dt] = round(surge, 2)
                    else:
                        error_cnt += 1
                        logger.error(
                            f"Out of range surge value [{surge}] for target {in_utc}"
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

    return surges_dict


def get_best_historic_surge(
    timeline: Timeline, noaa_station_id: str, bias_number: int
) -> dict:
    """Get the last known surge predictions for the past times in the timeline.

    Args:
        timeline (Timeline): a Timeline containing some past times.
        noaa_station_id (str): NOAA station id
        bias_number: 1 or 2, or 3, meaning which stored bias value to add to the surge values instead
            of the default bias.  None for neither.  This is for A/B testing of calculated bias logic.
            None for neither.  This is for A/B testing of calculated bias logic.

    Returns:
        dict: biased surge values, keyed by datetime, for all past times in the timeline.
    """
    data = {}
    if timeline.is_all_future():
        return data

    qs = Surge.objects.filter(
        noaa_id=noaa_station_id, tide_time__range=(timeline.start_dt, timeline.now)
    ).order_by("tide_time")

    for rec in qs:
        in_tz = rec.tide_time.astimezone(timeline.time_zone)
        if (
            (bias_number == 1 and rec.calc_bias is None)
            or (bias_number == 2 and rec.calc_bias2 is None)
            or (bias_number == 3 and rec.calc_bias3 is None)
        ):
            # skip it, not worth showing on the graph.
            continue
        surge = rec.surge
        if bias_number == 1:
            surge += rec.calc_bias
        elif bias_number == 2:
            surge += rec.calc_bias2
        elif bias_number == 3:
            surge += rec.calc_bias3
        else:
            surge += rec.bias or 0
        data[in_tz] = surge

    return data
