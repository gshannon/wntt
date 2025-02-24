from datetime import datetime
import os
import os.path
import csv
import logging
from app import tzutil as tz
from django.core.cache import cache
from django.conf import settings
from rest_framework.exceptions import APIException

# /surgedata is a mount defined in docker-compose.yml
surge_file_path = "/surgedata/surge-data.csv"
max_surge = 20
min_surge = -20
logger = logging.getLogger(__name__)


def get_surge_data(timeline, astro_levels, observed) -> (list, list, list):
    """ Get surge data that corresponds to the timeline. Surge data comprises past and/or future:
    1. Past surge, for datetimes prior to current clock time. These are computed as the difference between
    actual tide and predicted astronomical tide.
    2. Future surge, for datetimes later than current clock time. These are extracted from a csv file
    obtained from NOAA's NOMADS division (nomads.ncep.noaa.gov) for the Wells, ME station.

    Returns 3 lists, all of which correspond to the full timeline. Each list will populate a separate plot in the graph.
    - past surges, with None for any corresponding future datetime, or if incomplete past data
    - future surges, with None for any corresponding past datetime, or if missing future data. Entire list
        is returned as None if all values are None, and the plot will be skipped.
    - future storm tides -- predicted tide + storm surge for all future datetimes. None for past or missing data.
        Entire list is returned as None if all values are None, and the plot will be skipped.
    """
    now = tz.now(timeline[0].tzinfo)
    includes_past = timeline[0] < now
    includes_future = timeline[-1] >= now

    if includes_past and observed is None:
        logger.error("expected some observed levels, but got none")
        raise APIException()

    past_surge_data = []
    future_surge_data = []
    future_storm_tide = []
    projected_found = False
    future_storm_tide_found = False

    # Past Surge
    ii = 0
    if includes_past:
        for ii, (dt, astro, act) in enumerate(zip(timeline, astro_levels, observed)):
            if dt < now:
                future_surge_data.append(None)
                future_storm_tide.append(None)
                if astro is not None and act is not None:
                    past_surge_data.append(act - astro)
                else:
                    past_surge_data.append(None)
            else:
                break

    if includes_future:
        surge_dict = get_or_load_projected_surge_file(now)
        last_surge_value = None
        last_surge_value_used_count = 0
        for (dt, astro) in zip(timeline[ii:], astro_levels[ii:]):
            past_surge_data.append(None)
            # Since surge values are only hourly, we use the most recent seen when we don't have one for this time.
            # If we just leave the surge data None, plotly will report nearby values in the hover, in parens,
            # which messes up the math.
            # However, we only do this 3 times, i.e. to fill in one hour.  After that, there's just no surge data.
            surge_value = None
            if dt in surge_dict:
                surge_value = last_surge_value = surge_dict.get(dt)
                last_surge_value_used_count = 0
            elif last_surge_value_used_count < 3:
                surge_value = last_surge_value
                last_surge_value_used_count += 1

            if surge_value is not None:
                future_surge_data.append(surge_value)
                projected_found = True
                if astro is not None:
                    future_storm_tide.append(astro + surge_value)
                    future_storm_tide_found = True
                else:
                    future_storm_tide.append(None)
            else:
                future_surge_data.append(None)
                future_storm_tide.append(None)

    return (past_surge_data if includes_past else None,
            future_surge_data if projected_found else None,
            future_storm_tide if future_storm_tide_found else None)


def get_or_load_projected_surge_file(after: datetime) -> dict:

    """The csv file containing the projected surge data is updated on the NOAA site every 6 hours,
    and is downloaded by a cron job. Once loaded, its contents are cached for performance.
    So here, we have to determine if the disk file has been replaced since we last processed it. Therefore,
    if surge data file exists and has not been replaced by a newer download file, read the cache.
    Otherwise, read the download file, throwing out all but xx:00 and xx:30 (since the data is in 6-minute intervals
    and we show 15-min intervals and the others can't be displayed on the graph), and throwing out data older than
    the 'after' parameter, since it can hereafter never be displayed. Then save that to cache and return it.  We
    also skip any surge values >= 20, such as 9999.99.

    All datetimes in the file are in UTC, and are converted as necessary to the timezone of the given datetime param.

    Returns dict : the data, key = datetime, value = float surge value
    """

    # Since this is a small cache (< 1Kb), we'll use the process ID as the cache key, so each worker can have its own copy.  
    # This should avoid any multi-threading issues when setting the cache with multiple workers.
    pid = os.getpid()
    # The cached data is a dict with keys 'id' and 'data'.  'id' is the file's mtime, 'data' is the surge data.
    cached = cache.get(pid)
    logger.debug(f"found surge cache for process {pid}? {cached is not None}")
    if cached is not None:
        logger.debug(f"cached id: {cached['id']}")
    
    file_id = os.path.getmtime(surge_file_path) if os.path.isfile(surge_file_path) and os.access(surge_file_path, os.R_OK) else None
    logger.debug(f"current file id: {file_id}")
    if file_id is None:
        if cached is None:
            logger.error(f"{surge_file_path} is not found, and there is no cached surge data.")
            return {}
        else:
            logger.error(f"Can't read {surge_file_path} file, will use cache for now!")
            return cached['data']

    # So now we know the file exists and is readable.  If we have cached data, check if the file has been updated.
    if cached is not None and file_id == cached['id']:
        logger.debug(f"id from cache matches file id: {file_id}")
        return cached['data'] # return the cached data
    
    logger.debug(f"will cache/re-cache surge data, file id = {file_id}")

    surge_data = {}  # key=datetime, value=surge
    logger.debug(f'Reading {surge_file_path}')
    try:
        """Sample data:
                TIME,    TIDE,      OB,   SURGE,    BIAS,      TWL
        202502181200,   2.275,9999.000,  -1.600,9999.000,   0.675
        202502181206,   2.119,9999.000,9999.000,9999.000,9999.000
        202502181212,   1.970,9999.000,9999.000,9999.000,9999.000
        202502181218,   1.829,9999.000,9999.000,9999.000,9999.000
        202502181224,   1.695,9999.000,9999.000,9999.000,9999.000
        202502181230,   1.570,9999.000,9999.000,9999.000,9999.000
        ...
        """
        with open(surge_file_path) as surge_file:
            reader = csv.reader(surge_file, skipinitialspace=True)
            next(reader)  # skip header row
            for row in reader:
                # Surge values for Wells data is on the hour only, but the data file has a row for every 6 min.
                # Only the times that are multiples of 100 have actual surge data.
                if int(row[0]) % 100 != 0:
                    continue
                # All file datetimes are UTC. Convert to requested tz.
                in_utc = datetime.strptime(row[0], "%Y%m%d%H%M").replace(tzinfo=tz.utc)
                local_dt = in_utc.astimezone(after.tzinfo)
                if local_dt <= after:  # don't bother loading surge data that will never be displayed
                    continue
                try:
                    surge = float(row[3])
                    if min_surge <= surge <= max_surge:
                        surge_data[local_dt] = round(surge, 2)
                    else:
                        logger.error(f"Found unexpected surge value [{surge}] for target {in_utc}")
                except ValueError:
                    logger.error(f"Invalid surge value: '{row[3]}'")
    except FileNotFoundError:
        logger.error(f'Prediction file not found: {surge_file_path}')
        raise APIException()

    cache.set(pid, {'id': file_id, 'data': surge_data}, timeout = 60 * 60 * 6)  # 6 hour TTL
    logger.debug(f"Cached for worker {pid}, {len(surge_data)} values from {surge_file_path}")
    return surge_data
