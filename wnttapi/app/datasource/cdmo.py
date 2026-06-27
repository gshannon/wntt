import logging
import time
import xml.etree.ElementTree as ElTree
from datetime import date, datetime, timedelta
from enum import Enum

from app import tzutil as tz
from app import util
from app.hilo import Hilo, ObservedHighOrLow
from app.station import Station
from app.timeline import GraphTimeline, Timeline

from ..models import Water, Wind, get_station
from .soap import SoapClient


class Param(Enum):
    Tide = "Level", "level"
    Temperature = "Temp", "temp"
    WindSpeed = "Wspd", "speed"
    WindGust = "MaxWspd", "gust"
    WindDir = "Wdir", "dir_deg"

    def __new__(cls, name, label):
        obj = object.__new__(cls)
        obj._value_ = name  # matches CDMO parameter name
        obj.label = label  # matches the model property name
        return obj


WATER_PARAMS = [Param.Tide, Param.Temperature]
WIND_PARAMS = [Param.WindSpeed, Param.WindGust, Param.WindDir]

"""
Access CDMO web services to retrieve observed tide, wind, and temperature data. 
"""

logger = logging.getLogger(__name__)
# Min and max sane tide feet mllw/feet
(_min_tide, _max_tide) = (-5.0, 20.0)
_max_wind_speed = 120  # max sane wind speed in mph
_missing_data_value = -99.99
_request_time_warning_seconds = 5


def get_water_data(station: Station, timeline: Timeline, useDb: bool = True) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Paramters:
    station (Station): the station object
    timeline (Timeline): the timeline of datetimes to fetch data for
    useDb (bool): pull from database instead of calling cdmo, default True

    Returns:
    {dt: {"level": <value>, "temp": <value>}}
    """
    water_dict = {}

    if timeline.is_all_future():
        return water_dict  # Nothing to fetch

    if useDb:
        logger.debug(
            f"station.id={station.id} fetching water params for {timeline.start_dt} to {timeline.end_dt} from database"
        )
        use_padding = isinstance(timeline, GraphTimeline)
        start_dt = timeline.get_min(use_padding)
        end_dt = timeline.get_max(use_padding)

        # query must pass UTC datetimes as strings in ISO format: "2024-01-01T05:30:00+00:00"
        start_param = start_dt.astimezone(tz.utc).isoformat()
        end_param = end_dt.astimezone(tz.utc).isoformat()

        queryset = Water.objects.filter(
            station__exact=get_station(station.id), time__range=(start_param, end_param)
        ).order_by("time")
        logger.debug(
            f"Found {queryset.count()} rows in db for {station.id} from {start_dt} to {end_dt}"
        )
        for rec in queryset:
            in_utc = datetime.fromisoformat(rec.time)
            dt_in_local = in_utc.astimezone(timeline.time_zone)
            water_dict[dt_in_local] = {
                Param.Tide.label: rec.level,
                Param.Temperature.label: rec.temp,
            }

    else:
        logger.debug(
            f"station.id={station.id} pulling {WATER_PARAMS} for {timeline.start_dt} to {timeline.end_dt} from cdmo"
        )
        water_dict = get_cdmo(timeline, station, WATER_PARAMS)
        logger.debug(f"Total raw water data points: {len(water_dict)}")

    return water_dict


def get_wind_data(station: Station, timeline: Timeline, useDb: bool = True) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Args:
    station (Station): the station object
    timeline (Timeline): the timeline of datetimes to fetch data for
    useDb (bool): pull from database instead of calling cdmo, default True

    Returns:
    -{dt: {"speed": <value>, "gust": <value>, "dir_deg": <value> }}
    """

    wind_dict = {}

    # If timeline is all in the future, don't bother.
    if timeline.is_all_future():
        return wind_dict

    if useDb:
        use_padding = isinstance(timeline, GraphTimeline)
        start_dt = timeline.get_min(use_padding)
        end_dt = timeline.get_max(use_padding)

        # query must pass datetimes as strings in ISO format: "2024-01-01T05:30:00+00:00"
        start_param = start_dt.astimezone(tz.utc).isoformat()
        end_param = end_dt.astimezone(tz.utc).isoformat()

        queryset = Wind.objects.filter(
            station__exact=get_station(station.id), time__range=(start_param, end_param)
        ).order_by("time")
        logger.debug(
            f"Found {queryset.count()} rows in db for {station.id} from {start_dt} to {end_dt}"
        )
        if queryset.count() == 0:
            return wind_dict

        # TODO: make gust NOT NULL in database.
        for rec in queryset:
            in_utc = datetime.fromisoformat(rec.time)
            dt_in_local = in_utc.astimezone(timeline.time_zone)

            wind_dict[dt_in_local] = {
                Param.WindSpeed.label: rec.speed,
                Param.WindGust.label: rec.gust,
                Param.WindDir.label: rec.dir_deg,
            }

    else:
        logger.debug(
            f"station.id={station.id} pulling {WIND_PARAMS} for {timeline.start_dt} to {timeline.end_dt} from cdmo"
        )
        wind_dict = get_cdmo(
            timeline,
            station,
            [Param.WindSpeed, Param.WindGust, Param.WindDir],
        )
        logger.debug(f"Total raw wind data points: {len(wind_dict)}")

        if len(wind_dict) == 0:
            logger.warning(
                "Got no wind data for %s, %s - %s",
                station.id,
                timeline.start_dt,
                timeline.end_dt,
            )
            return wind_dict

    return wind_dict


def get_cdmo(timeline: Timeline, station: Station, params: list) -> dict:
    """
    Get XML data from CDMO, parse it, convert to requested timezone.
    As of Feb 2024, these CDMO endpoints will return a maximum of 1000 data points. At 96 points per day (4 per hour),
    that's about 10.5 days. Therefore, no more than 10 days should be requested.  If you ask for more, CDMO truncates
    data points starting from the oldest data, not the latest.  So care should be taken not to ask for too much,
    else data at the beginning of the graph will be missing.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the swmp station object
    - params: list of requested CDMO parameters

    Returns:
    - {dt: {<param-label>: <value}}  (Param labels are 'level' and 'temp")

    """
    if station is None:
        raise util.InternalError("station is required")

    # validate that timeline datetimes are on 15-minute intervals and seconds=0
    if timeline.start_dt.minute % 15 > 0 or timeline.start_dt.second > 0:
        # CDMO data is always on 15-minute intervals.
        raise util.InternalError("datetimes must be on 15-minute intervals")

    xml = get_cdmo_xml(timeline, station, params)
    return parse_cdmo_xml(timeline, station, xml, params)


def get_cdmo_xml(timeline: Timeline, station: Station, params: list) -> dict:
    """
    Retrieve CDMO data as requested. Returns the xml returned from CDMO as a string.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the swmp station object
    - params: list of requested CDMO parameters

    Returns:
    - {dt: {<param-label>: <value}}
    """
    # Because CDMO returns units of entire days using LST, we may need to adjust the dates we request.
    # When getting Level data, we add padding before and after to help determine highs/lows when they are near the boundaries.
    use_padding = Param.Tide in params and isinstance(timeline, GraphTimeline)

    req_start_date, req_end_date = compute_cdmo_request_dates(
        timeline.get_min(use_padding), timeline.get_max(use_padding)
    )

    # TODO: This should be a bit more robust?
    data_station_id = (
        station.id
        if Param.Tide in params or Param.Temperature in params
        else station.weather_station_id
    )

    try:
        start_time = time.time()
        logger.debug(f"Calling CDMO for {params} {req_start_date} to {req_end_date}")
        param_str = ",".join(p.value for p in params)
        xml = SoapClient.get_client().service.exportAllParamsDateRangeXMLNew(
            data_station_id, req_start_date, req_end_date, param_str
        )
        elapsed_sec = time.time() - start_time
        if elapsed_sec > _request_time_warning_seconds:
            logger.warning(
                f"Call to CDMO with param {param_str} took {round(elapsed_sec, 2)}"
            )

    except Exception as exc:
        elapsed_sec = time.time() - start_time
        msg = f"Error getting {param_str} data {req_start_date} to {req_end_date} from CDMO, time={round(elapsed_sec, 2)}: {str(exc)}"
        if "urlopen" in str(exc):
            # unfortunately this happens often & we don't want to clutter the sentry logs
            logger.warning(msg)
        else:
            logger.error(msg)
        exc.add_note("param: %s %s to %s" % (param_str, req_start_date, req_end_date))
        raise exc

    logger.debug(
        f"Got {param_str} data {req_start_date} to {req_end_date} time {round(elapsed_sec, 2)} sec"
    )
    return xml


def parse_cdmo_xml(
    timeline: Timeline, station: Station, xml: str, params: list
) -> dict:
    """
    Parse the data returned from CDMO for the requested timeline.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the swmp station object
    - param: list of requested CDMO parameters

    Returns:
    - {dt: {<param-label>: <value> [, ...]}}

    """
    datadict = {}

    if xml is None or len(xml) == 0:
        return datadict

    # We need to pull data for the padded timeline, for hi/lo functionality, not just
    # display times. No sense looking for future, these are observations. If asking for
    # tide level, we need a padded timeline to identify highs and lows that are near the edges of the timeline.
    past_timeline = timeline.get_all_past(
        padded=isinstance(timeline, GraphTimeline) and Param.Tide in params
    )

    root = ElTree.fromstring(xml)  # ElementTree.Element
    text_error_check(root)
    records = ignored = none_or_bad = 0
    for reading in root.findall(".//data"):  # use XPATH to dig out our data points
        records += 1
        # we use utcStamp, not the DateTimeStamp because the latter is in LST, not sensitive to DST.
        date_str = reading.find("./utcStamp").text
        try:
            naive_utc = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        except ValueError:
            none_or_bad += 1
            logger.error("Skipping bad datetime '%s'", date_str)
            continue

        # We need this local time. First promote to UTC.
        in_utc = naive_utc.replace(tzinfo=tz.utc)
        # Now convert to requested tzone, so DST is handled properly
        dt_in_local = in_utc.astimezone(timeline.time_zone)
        # Since we query more data than we need, only save the data that is in the requested timeline.
        # For GraphTimeline's, this includes any padded times for hi/lo functionality.
        if dt_in_local not in past_timeline:
            ignored += 1
            continue

        # Extract and convert all the params we're looking for.
        obj = {}
        for param in params:
            try:
                data_str = reading.find(f"./{param.value}").text
                value = convert(data_str, param, station, dt_in_local)
                if value is None:
                    none_or_bad += 1
                else:
                    obj[param.label] = value
            except (TypeError, ValueError, AttributeError):
                none_or_bad += 1
                logger.error(
                    "Invalid or missing %s for %s: '%s'",
                    param.value,
                    naive_utc,
                    data_str,
                )
        # Keep this data point only if we got valid values for all requested parameters.
        if len(obj) == len(params):
            datadict[dt_in_local] = obj

    timeline_len = len(past_timeline)
    failure_rate = 100 - int(round(len(datadict) / len(past_timeline), 2) * 100)

    logger.debug(
        "For {}, using {} out of {} requested, failrate={}% tl=[{} - {}] records={} out-of-range={} none+bad={}".format(
            params[0],
            len(datadict),
            timeline_len,
            failure_rate,
            past_timeline[0],
            past_timeline[-1],
            records,
            ignored,
            none_or_bad,
        )
    )

    # XML data is returned in reverse chronological order. Reverse it here.
    return dict(reversed(list(datadict.items())))


def convert(
    data_str: str, param: Param, station: Station, local_dt: datetime
) -> callable:
    """Perform the proper data conversion for the param value."""
    match param:
        case Param.Tide:
            return handle_navd88_level(data_str, local_dt, station)
        case Param.WindSpeed | Param.WindGust:
            return handle_windspeed(data_str, local_dt)
        case Param.WindDir:
            return handle_int(data_str, local_dt)
        case Param.Temperature:
            return handle_centigrade(data_str, local_dt)
        case _:
            raise util.InternalError(f"No converter defined for param {param}")


def text_error_check(rootElement):
    """If a node is not supposed to have text, return that text, else None
    This is how CDMO returns an error e.g. Invalid IP address.
    """
    data_node = rootElement.find(".//data")
    try:
        message = data_node.text.strip()
        if len(message) > 0:
            logger.error("Received unexpected message from CDMO: %s", message)
            raise Exception(f"CDMO returned: {message}")
    except AttributeError:
        pass  # Not every payload has text in their data node


def compute_cdmo_request_dates(
    start_time: datetime, end_time: datetime
) -> tuple[date, date]:
    """
    CDMO will give us only full days of data, using LST of the time zone of the requesting station. LST
    does not honor DST, so we may have to adjust the start date and/or the end date, to avoid missing data
    or getting too much data. We depend on the timeline being chronologically ordered. Here is the logic:

    - Start date: If timeline starts in standard time, no change.  Else if timeline starts in DST and
    asks for anything before 01:00, we must ask for the previous day, else we'll miss that hour.

    - End date: If timeline ends in standard time, no change.  Else if timeline ends in DST and asks for
    only data in the first hour, we won't need that date since it will be included in data for the previous
    day, so we bump back the end date. (Note that this can never push it back before the requested
    start date. In the extreme case of asking for a single datapoint, the start date would have also been pushed
    back.
    """

    requested_start_date = start_time.date()
    requested_end_date = end_time.date()

    if tz.isDst(start_time) and start_time.hour < 1:
        requested_start_date -= timedelta(days=1)

    if tz.isDst(end_time) and end_time.hour < 1:
        requested_end_date -= timedelta(days=1)

    logger.debug(
        f"Timeline: {start_time.strftime('%Y-%m-%d %H:%M')} "
        f"- {end_time.strftime('%Y-%m-%d %H:%M')}, "
        "Requesting CDMO dates: "
        f"{requested_start_date.strftime('%Y-%m-%d')} - "
        f"{requested_end_date.strftime('%Y-%m-%d')}"
    )

    return requested_start_date, requested_end_date


def find_all_hilos(
    timeline: GraphTimeline, water_dict: dict, astro_pred_dict: dict
) -> dict:
    """Build a dense dict of high and low tides times from observed and predicted tide data. If there is missing
    observed data that makes it impossible to determine a high or low observed tide, we'll substitute the
    predicted value, so it can be labelled on the graph, and still appear in HiLo mode.

    Args:
    - timeline: key-ordered Timeline of datetimes for the graph
    - obs_dict: dense dict of observed tide readings {datetime: {"level": val, "temp": val"}}
    - astro_pred_dict: dense dict of predicted high and low tides covering the timeline.
        {timeline_dt: PredictedHighOrLow}

    Returns:
        sparse dict of {dt: HighOrLow} indicating which datetimes are high or low tides.
    """

    hilomap = {}  # {dt: HighLowEvent}

    past_padded_timeline = timeline.get_all_past(padded=True)

    # Use the sparse predicted highs/lows to drive the logic. Since actual highs/lows will occur fairly close
    # to the predicted, this way we can simplify the identification of observed highs and lows, which may contain
    # missing data, and sometimes move erratically. Here, we just use the highest or lowest observed value in
    # a range of times surrounding the predicted value.
    # TODO: Handle edge case where observed high or low is missing and we falsely report a nearby value instead.
    for dt, pred in astro_pred_dict.items():
        if (
            len(past_padded_timeline) == 0
            or dt < past_padded_timeline[0]
            or dt > past_padded_timeline[-1]
        ):
            hilomap[dt] = pred
            continue
        # Find the time with the highest or lowest observed value within 1 hour of the predicted time.
        search_start = dt - timedelta(minutes=60)
        search_end = dt + timedelta(minutes=60)
        candidate_times = list(
            filter(lambda t: search_start <= t <= search_end, past_padded_timeline)
        )
        observed = {t: water_dict.get(t, None) for t in candidate_times}
        observed = {k: v for k, v in observed.items() if v is not None}
        if len(observed) > 0:
            if pred.hilo == Hilo.HIGH:
                observed_hilo_dt = max(
                    observed.items(), key=lambda tup: tup[1].get(Param.Tide.label)
                )[0]
            else:
                observed_hilo_dt = min(
                    observed.items(), key=lambda tup: tup[1].get(Param.Tide.label)
                )[0]
            hilomap[observed_hilo_dt] = ObservedHighOrLow(
                observed[observed_hilo_dt][Param.Tide.label], pred.hilo
            )
        else:
            # No observed data near this predicted high/low. Just use the predicted time.
            logger.debug(
                f"No observed data near predicted {pred.hilo} at {dt}, using predicted time"
            )
            hilomap[dt] = pred

    return hilomap


def clean_tide_data(in_dict: dict, station: Station) -> dict:
    """Strip out one kind of known data error from CDMO. Sometimes when CDMO doesn't have a good value for
    a data point it sends a 0 value (navd88).  While zero tide is a possible real value, if there are multiple
    zeros in a row, or a zero that constitutes a large, unreasonable jump from the previous value, then we
    just reject those values as bad data. Since values are sent in NAVD88, and at this point, all values are converted to MLLW, we have to convert back
    to navd88 feet to do this analysis. We will reject any zero value that is not immediately preceeded or followed
    by a non-zero value between -1 and +1 ft.
    TODO: Remove this if this issue is addressed.

    Args:
        in_dict: the dt:val dict in chronological order
        station (Station): The station object, so we can access the MLLW conversion

    Returns:
        dict: Same as passed in dict, with bad data removed.
    """

    class CleanStatus(Enum):
        ACCEPT = 1
        REJECT = 2
        UNKNOWN = 3
        ZERO = 4

    keys = list(in_dict.keys())
    first_bad_dt = None
    reject_cnt = 0

    # Examine the data prior to the zero found at this index, if any.
    def look_back(idx, dt) -> CleanStatus:
        if idx == 0:
            return CleanStatus.UNKNOWN
        prev_dt = keys[idx - 1]
        if dt - prev_dt > timedelta(minutes=15):
            return CleanStatus.UNKNOWN
        prev_navd_feet = in_dict[prev_dt] - station.mllw_conversion
        if prev_navd_feet == 0:
            return CleanStatus.ZERO
        return CleanStatus.ACCEPT if -1 <= prev_navd_feet <= 1 else CleanStatus.REJECT

    # Examine the data after the zero found at this index, if any.
    def look_ahead(idx, dt) -> bool:
        if idx >= len(keys) - 1:
            return False
        next_dt = keys[idx + 1]
        if next_dt - dt > timedelta(minutes=15):
            return False
        next_navd_feet = in_dict[next_dt] - station.mllw_conversion
        if next_navd_feet == 0:
            return False
        return -1 <= next_navd_feet <= 1

    def is_valid(idx, dt):
        nonlocal keys
        nonlocal first_bad_dt
        nonlocal reject_cnt

        navd_feet = in_dict[dt] - station.mllw_conversion

        if navd_feet == 0:
            accept = False
            match look_back(idx, dt):
                case CleanStatus.ACCEPT:
                    accept = True  # No need to check ahead also
                case CleanStatus.UNKNOWN | CleanStatus.ZERO:
                    if look_ahead(idx, dt):
                        accept = True  # Passed the ahead check, so OK
                case CleanStatus.REJECT:
                    pass

            if not accept:
                reject_cnt += 1
                if first_bad_dt is None:
                    first_bad_dt = dt
                logger.debug(f"Rejecting value 0 navd88 at {dt}")
            return accept

        return True

    cleaned = {dt: in_dict[dt] for idx, dt in enumerate(keys) if is_valid(idx, dt)}
    if reject_cnt > 0:
        logger.warning(
            "for %s, rejected %d out of %d with value nav 0, first=%s",
            station.id,
            reject_cnt,
            len(in_dict),
            first_bad_dt,
        )
    return cleaned


def handle_float(data_str: str, local_dt: datetime) -> float:
    """Convert string to float. Returns None if bad data."""
    if data_str is None or len(data_str.strip()) == 0:
        return None
    try:
        value = float(data_str)
    except ValueError:
        logger.error("Invalid float for %s: '%s'", local_dt, data_str)
        value = None
    return value


def handle_centigrade(data_str: str, local_dt: datetime) -> float:
    """Convert string to float. Returns None if bad data."""
    if data_str is None or len(data_str.strip()) == 0:
        return None
    try:
        value = util.centigrade_to_fahrenheit(float(data_str))
    except ValueError:
        logger.error("Invalid temperature for %s: '%s'", local_dt, data_str)
        value = None
    return value


def handle_int(data_str: str, local_dt: datetime) -> int:
    """Convert string to float. Returns None if bad data."""
    if data_str is None or len(data_str.strip()) == 0:
        return None
    try:
        value = int(data_str)
    except ValueError:
        logger.error("Invalid int for %s: '%s'", local_dt, data_str)
        value = None
    return value


def handle_navd88_level(level_str: str, local_dt: datetime, station: Station) -> float:
    """Convert tide string in navd88 meters to MLLW feet. Returns None if bad data."""
    if level_str is None or len(level_str.strip()) == 0:
        logger.warning(f"skipping [{level_str}] at {local_dt}")
        return None
    try:
        read_level = float(level_str)
        level = station.navd88_meters_to_mllw_feet(read_level)
        if level < _min_tide or level > _max_tide:
            if read_level != _missing_data_value:  # CDMO missing data code
                logger.error(
                    "level out of range for %s: %s (raw: %s)",
                    local_dt,
                    level,
                    read_level,
                )
            level = None
    except ValueError:
        logger.error("invalid level: [%s]", level_str)
        level = None
    return level


def handle_windspeed(wspd_str: str, local_dt: datetime):
    """Convert wind speed string in meters per sec to miles per hour. Returns None if bad data."""
    if wspd_str is None or len(wspd_str.strip()) == 0:
        return None
    try:
        read_wspd = float(wspd_str)
        mph = util.meters_per_second_to_mph(read_wspd)
        if mph < 0 or mph > _max_wind_speed:
            logger.error(
                "wind speed out of range for %s: %s mps converted to %s mph",
                local_dt,
                read_wspd,
                mph,
            )
            mph = None
    except ValueError:
        logger.error("invalid windspeed: [%s]", wspd_str)
        mph = None
    return mph
