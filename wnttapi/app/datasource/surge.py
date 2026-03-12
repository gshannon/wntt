import csv
import logging
import os
import os.path
import re
from datetime import datetime, timedelta

import sentry_sdk
from app import tzutil as tz
from app.timeline import GraphTimeline
from django.core.cache import cache

from ..models import Surge, SurgeBias

# /surgedata is a mount defined in docker-compose.yml
_default_surge_file_dir = "/data/surge/data"
_max_surge = 20
_min_surge = -20
_no_value = "9999.000"

logger = logging.getLogger(__name__)


def get_future_surge_data(
    timeline: GraphTimeline,
    noaa_station_id: str,
    last_recorded_dt: datetime,
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
        dict: {
            "surges": dict {<dt>: <surge>}
            "bias": <calculated bias, or None>,
        }

    """
    future_surge_dict = {}  # {dt: surge_value}

    # Don't bother looking for data more than 6 days in the future.
    if timeline.end_dt >= timeline.now and timeline.start_dt < timeline.now + timedelta(
        days=6
    ):
        future_surge_dict = get_or_load_projected_surge_file(noaa_station_id, timeline)
        # If there's any recorded tides in the timeline, we don't want any data for those times.
        if last_recorded_dt is not None:
            future_surge_dict["surges"] = {
                dt: val
                for dt, val in future_surge_dict["surges"].items()
                if dt > last_recorded_dt
            }

    return future_surge_dict


"""
    Get the last known surge predictions for the past times in the timeline.
    Params:
    - timeline: timeline
    - noaa_station_id: the NOAA station code so we can get the right data
    - use_calculated_bias: if True and station has calculated bias, add that to the surge values. This is for
      A/B testing of calculated bias logic.
"""


def get_best_historic_surge(
    timeline: GraphTimeline, noaa_station_id: str, use_calculated_bias: bool
) -> dict:
    data = {}
    if timeline.is_all_future():
        return data

    qs = Surge.objects.filter(
        noaa_id=noaa_station_id, tide_time__range=(timeline.start_dt, timeline.now)
    ).order_by("tide_time")

    for rec in qs:
        in_tz = rec.tide_time.astimezone(timeline.time_zone)
        if use_calculated_bias and rec.calc_bias is None:
            # skip it, not worth showing on the graph.
            continue
        surge = rec.surge
        if use_calculated_bias:
            surge += rec.calc_bias or 0
        else:
            surge += rec.bias or 0
        data[in_tz] = surge

    logger.debug(data)
    return data


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
    noaa_station_id: str,
    timeline: GraphTimeline,
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
        timezone (ZoneInfo): Timezone to convert to.
        surge_file_dir (str, optional): for testing, use to override standard surge file location.

    Returns:
        dict: {
            "surges": dict {<dt>: <surge>}
            "bias": <calculated bias, or None>,
        }
    """
    logger.debug(f"looking in surge cache for station {noaa_station_id}...")

    # pull the existing cache value, if any
    entry = cache.get(noaa_station_id)
    if entry is not None:
        logger.debug(
            f"cache exists for {noaa_station_id} filedate {entry.get('filedate', None)}, cycle {entry.get('cycle', None)}, data from {min(entry['data']) if entry['data'] else 'N/A'} to {max(entry['data']) if entry['data'] else 'N/A'}"
        )
    else:
        logger.debug("nothing in cache")

    # Find the last file available for this noaa station. Normally
    # there should be just one file there.
    pattern = r"(\d+)-(\d+)-(\d\d).csv$"  # e.t. 8419317-20260213-06.csv
    filepath, filedate, cycle = None, None, None
    with os.scandir(surge_file_dir) as entries:
        for e in entries:
            matches = re.findall(
                pattern, e.name
            )  # returns list of tuples, not None if no match
            if len(matches) == 1 and matches[0][0] == noaa_station_id:
                # Got it. Extract the filedate & cycle from the file name.
                filepath = os.path.join(surge_file_dir, e.name)
                filedate, cycle = (
                    matches[0][1],
                    int(matches[0][2]),
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
        return entry.get("data", {})

    # If we have already cached this file, just return that.
    if entry is not None:
        if filedate == entry.get("filedate") and cycle == entry.get("cycle"):
            logger.debug(
                f"cache match: {noaa_station_id}, {filedate}/{cycle} {min(entry['data'])} - {max(entry['data'])} "
            )
            return entry["data"]
        else:
            # There's a newer file for this cached station. We'll be replacing with a new one..
            logger.debug(
                f"Will replace old cache for {noaa_station_id}, {filedate}/{cycle}"
            )

    # Get bias
    calculated_bias = None
    record = SurgeBias.objects.filter(
        noaa_id=noaa_station_id, filedate=filedate, cycle=cycle
    ).first()
    if record is None:
        logger.debug(
            f"Bias record not found in db for {noaa_station_id} {filedate} cycle {cycle}."
        )
    else:
        calculated_bias = record.bias
        logger.debug(
            f"got bias id {record.id}: {record.bias} from db for {noaa_station_id} {filedate} cycle {cycle}"
        )

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
                        float(bias_str)
                        if calculated_bias is None and bias_str != _no_value
                        else 0
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
        return {}

    # Cache the data. We'll use a TTL of 48 hours to handle cases where download fails a few times.
    payload = {"surges": surges_dict, "bias": calculated_bias}
    cache.set(
        noaa_station_id,
        {"filedate": filedate, "cycle": cycle, "data": payload},
        timeout=60 * 60 * 48,
    )
    logger.debug(
        f"{noaa_station_id}: cached {len(surges_dict)} surge values, from {min(surges_dict)} to {max(surges_dict)}"
    )
    return payload
