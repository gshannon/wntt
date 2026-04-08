import logging
import os
import time
import xml.etree.ElementTree as ElTree
from datetime import date, datetime, timedelta
from enum import Enum

from app import tzutil as tz
from app import util
from app.datasource.custom_transport import CustomTransport
from app.hilo import Hilo, ObservedHighOrLow
from app.station import Station
from app.timeline import GraphTimeline, Timeline
from suds.client import Client


class Param(Enum):
    Tide = "Level"
    AllWind = "Wspd,MaxWspd,Wdir"
    WindSpeed = "Wspd"
    WindGust = "MaxWspd"
    WindDir = "Wdir"
    Temperature = "Temp"


"""
Access CDMO web services to retrieve observed tide, wind, and temperature data. 
"""

logger = logging.getLogger(__name__)
_cdmo_wsdl = "https://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl"
# Min and max sane tide feet mllw/feet
(_min_tide, _max_tide) = (-5.0, 20.0)
_max_wind_speed = 120  # max sane wind speed in mph
_missing_data_value = -99.99
_request_timeout_seconds = 30
_request_time_warning_seconds = 5


class SoapClient:
    """Singleton class to hold the suds Client object, since creating it is expensive and seems to cause CDMO to reject the user/password if done on every request. This is a workaround until that issue is resolved."""

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            user_name = os.environ.get("CDMO_USER", None)
            password = os.environ.get("CDMO_PASSWORD", None)
            transport = (
                CustomTransport(user_name, password) if user_name and password else None
            )
            start_time = time.time()
            try:
                if transport is not None:
                    logger.debug(f"Creating Client with username {user_name}")
                    cls._client = Client(
                        _cdmo_wsdl,
                        retxml=True,
                        transport=transport,
                    )
                else:
                    logger.debug("Creating Client with no transport")
                    cls._client = Client(
                        _cdmo_wsdl,
                        retxml=True,
                    )
            except Exception as exc:
                elapsed_sec = time.time() - start_time
                logger.error(
                    f"Error creating Client, time {round(elapsed_sec, 2)} sec: {str(exc)}"
                )
                raise exc
            # This is the only way to override the default 90 sec.  Doesn't work in constructor.
            # cls._client.set_options(timeout=_request_timeout_seconds)
            elapsed_sec = time.time() - start_time
            logger.debug(f"Created Client object in {round(elapsed_sec, 2)} sec")
        return cls._client


def get_recorded_tides(station: Station, timeline: Timeline) -> dict:
    """Retrieve tide water levels from CDMO relative to MLLW feet.

    Args:
        station (Station): the station object
        timeline (Timeline): the timeline of datetimes to fetch data for

    Returns:
        dict: dense dict, {dt: level} where dt is a datetime in the timeline and level is the
        tide level in MLLW feet.
    """
    tide_dict = get_cdmo(timeline, station, [Param.Tide])[Param.Tide]
    # Clean the data of bogus zeros, i.e. any 0 that is more than 1 hour after the previous data.
    return clean_tide_data(tide_dict, station)


def get_water_data(station: Station, timeline: Timeline, params: list) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Args:
        station (Station): the station object
        timeline (Timeline): the timeline of datetimes to fetch data for

    Returns:
        dense dict of {param: data_dict}
        where each data_dict is dense dict of {param: {dt: {speed, gust, dir, dir_str}}}
    """
    if timeline.is_all_future():
        # Nothing to fetch
        return {}
    logger.debug(
        f"station.id={station.id} fetching {params} for {timeline.start_dt} to {timeline.end_dt}"
    )
    data = get_cdmo(timeline, station, params)
    if Param.Tide in params:
        data[Param.Tide] = clean_tide_data(data[Param.Tide], station)
    return data


def get_wind_data(station: Station, timeline: Timeline) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Args:
        station (Station): the station object
        timeline (Timeline): the timeline of datetimes to fetch data for

    Returns:
        dense dict of {dt: {speed, gust, dir, dir_str}}
    """

    wind_dict = {}

    # If timeline is all in the future, don't bother.
    if timeline.is_all_future():
        return wind_dict

    all_wind = get_cdmo(
        timeline,
        station,
        [Param.WindSpeed, Param.WindGust, Param.WindDir],
    )
    logger.debug(f"Wind speed data points: {len(all_wind[Param.WindSpeed])}")
    logger.debug(f"Wind gust data points: {len(all_wind[Param.WindGust])}")
    logger.debug(f"Wind direction data points: {len(all_wind[Param.WindDir])}")

    if len(all_wind[Param.WindSpeed]) == 0:
        logger.warning(
            "Got no wind speed data, station %s, timeline %s - %s",
            station.id,
            timeline.start_dt,
            timeline.end_dt,
        )
        return wind_dict

    return assemble_wind_data(all_wind)


def assemble_wind_data(wind_data: dict) -> dict:
    """Assemble wind data from the 3 component dicts into a single dict.

    Args:
        speed_dict (dict): dense dict of {dt: speed}
        gust_dict (dict): dense dict of {dt: gust}
        dir_dict (dict): dense dict of {dt: direction}
    Returns:
        dict: dense dict of {dt: {speed, gust, dir, dir_str}}
    """
    wind_dict = {}
    speed_dict = wind_data[Param.WindSpeed]
    gust_dict = wind_data[Param.WindGust]
    dir_dict = wind_data[Param.WindDir]

    # Assemble all the data.
    error_found = False
    for dt, speed in speed_dict.items():
        # Make sure we have all values, or none.
        if dt not in gust_dict or dt not in dir_dict:
            if not error_found:
                logger.error("Missing gust and/or direction wind data for %s", dt)
            error_found = True
            continue
        wind_dict[dt] = {
            "speed": speed,
            "gust": gust_dict[dt],
            "dir": dir_dict[dt],
            # The graph will display compass point names, so translate the direction into strings for dir_str.
            "dir_str": util.degrees_to_dir(dir_dict[dt]),
        }

    return wind_dict


def get_cdmo(timeline: Timeline, station: Station, params: list) -> dict:
    """
    Get XML data from CDMO, parse it, convert to requested timezone.
    As of Feb 2024, these CDMO endpoints will return a maximum of 1000 data points. At 96 points per day (4 per hour),
    that's about 10.5 days. Therefore, no more than 10 days should be requested.  If you ask for more, CDMO truncates
    data points starting from the oldest data, not the latest.  So care should be taken not to ask for too much,
    else data at the beginning of the graph will be missing.

    Parameters:
    timeline : datetimes (tz aware) requested by the user, in ordered 15-minute intervals
    station_id : id of water or weather station
    params : list of data parameter being requested
    converter : a function to convert a data point into the desired type, e.g. float or int, or unit conversion

    Returns:
        dense dict of values, {datetime: value}

    """
    if station is None:
        raise util.InternalError("station is required")

    # validate that timeline datetimes are on 15-minute intervals and seconds=0
    if timeline.start_dt.minute % 15 > 0 or timeline.start_dt.second > 0:
        # CDMO data is always on 15-minute intervals.
        raise util.InternalError("datetimes must be on 15-minute intervals")

    xml = get_cdmo_xml(timeline, station, params)
    data = parse_cdmo_xml(timeline, station, xml, params)
    return data


def get_cdmo_xml(timeline: Timeline, station: Station, params: list) -> dict:
    """
    Retrieve CDMO data as requested. Returns the xml returned from CDMO as a string.
    Params:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the CDMO station code
    - param: the CDMO param code
    """
    # Because CDMO returns units of entire days using LST, we may need to adjust the dates we request.
    # When getting Level data, we add padding before and after to help determine highs/lows when they are near the boundaries.
    use_padding = Param.Tide in params and isinstance(timeline, GraphTimeline)

    req_start_date, req_end_date = compute_cdmo_request_dates(
        timeline.get_min(use_padding), timeline.get_max(use_padding)
    )

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
        logger.error(
            f"Error getting {param_str} data {req_start_date} to {req_end_date} from CDMO, time={round(elapsed_sec, 2)}: {str(exc)}"
        )
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
    Parse the data returned from CDMO for the requested timeline. Returns a dense, key-ordered
    dict of {param: {dt: value}} where dt=datetime matching an element of the timeline and value = the data value.
    Params:
    - timeline: list of datetime representing what will be displayed on the graph
    - xml: string with the contents in XML format
    - param: the CDMO param code
    - converter: func to convert raw data to desired display value
    - minutes of each hour to include. XML will contain an entry for every 15 minutes
    """
    datadict = {}
    if xml is None or len(xml) == 0:
        return datadict

    for param in params:
        datadict[param] = {}

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
        for param in params:
            data_str = reading.find(f"./{param.value}").text
            try:
                value = convert(data_str, param, station, dt_in_local)
                if value is None:
                    none_or_bad += 1
                else:
                    datadict[param][dt_in_local] = value
            except (TypeError, ValueError):
                none_or_bad += 1
                logger.error(
                    "Invalid %s for %s: '%s'", param.value, naive_utc, data_str
                )

    min_len = min(len(datadict[param]) for param in params)
    timeline_len = len(past_timeline)
    failure_rate = 100 - int(round(min_len / len(past_timeline), 2) * 100)
    message = (
        f"For {param}, got {len(datadict)} out of {timeline_len}, failrate={failure_rate}% "
        + f"tl=[{past_timeline[0]} - {past_timeline[-1]}] "
        + f"records={records} out-of-range={ignored} none+bad={none_or_bad}"
    )

    if (timeline_len >= 96 and failure_rate > 20) or (
        timeline_len < 96 and failure_rate > 95
    ):
        logger.warning(message)
    else:
        logger.debug(message)

    # XML data is returned in reverse chronological order. Reverse it here.
    for param in params:
        datadict[param] = dict(reversed(list(datadict[param].items())))
    return datadict


def convert(
    data_str: str, param: Param, station: Station, local_dt: datetime
) -> callable:
    """Get the appropriate converter function for the given param."""
    match param:
        case Param.Tide:
            return handle_navd88_level(data_str, local_dt, station)
        case Param.WindSpeed | Param.WindGust:
            return handle_windspeed(data_str, local_dt)
        case Param.WindDir:
            return handle_int(data_str, local_dt)
        case Param.Temperature:
            return handle_float(data_str, local_dt)
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
    timeline: GraphTimeline, obs_dict: dict, astro_pred_dict: dict
) -> dict:
    """Build a dense dict of high and low tides times from observed and predicted tide data. If there is missing
    observed data that makes it impossible to determine a high or low observed tide, we'll substitute the
    predicted value, so it can be labelled on the graph, and still appear in HiLo mode.

    Args:
    - timeline: key-ordered Timeline of datetimes for the graph
    - obs_dict: dense dict of observed tide readings {datetime: level}
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
        # logger.debug(f"Considering predicted {pred} at {dt}")
        if len(past_padded_timeline) == 0 or dt > past_padded_timeline[-1]:
            hilomap[dt] = pred
            continue
        # Find the time with the highest or lowest observed value within 1 hour of the predicted time.
        search_start = dt - timedelta(minutes=60)
        search_end = dt + timedelta(minutes=60)
        candidate_times = list(
            filter(lambda t: search_start <= t <= search_end, past_padded_timeline)
        )
        observed = {t: obs_dict.get(t, None) for t in candidate_times}
        observed = {k: v for k, v in observed.items() if v is not None}
        if len(observed) > 0:
            if pred.hilo == Hilo.HIGH:
                observed_hilo_dt = max(observed, key=observed.get)
                # logger.debug(
                #     f"Highest observed was {observed[observed_hilo_dt]} at {observed_hilo_dt}"
                # )
            else:
                observed_hilo_dt = min(observed, key=observed.get)
                # logger.debug(
                #     f"Lowest observed was {observed[observed_hilo_dt]} at {observed_hilo_dt}"
                # )
            hilomap[observed_hilo_dt] = ObservedHighOrLow(
                observed[observed_hilo_dt], pred.hilo
            )
        else:
            # No observed data near this predicted high/low. Just use the predicted time.
            # logger.debug(
            #     f"No observed data near predicted {pred.hilo} at {dt}, using predicted time"
            # )
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
        logger.debug(f"skipping [{level_str}] at {local_dt}")
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
