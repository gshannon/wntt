import logging
import os
import xml.etree.ElementTree as ElTree
from datetime import date, datetime, timedelta
from enum import Enum

from rest_framework.exceptions import APIException

from app import tzutil as tz
from app import util
from app.datasource.winds import Winds
from app.hilo import Hilo, ObservedHighOrLow
from app.station import Station
from app.timeline import GraphTimeline, Timeline

from ..models import Water, Wind, get_station
from .soap import SoapClient
from .tides import Tides


class Param(Enum):
    LevelNav = "Level"
    CorrectedLevelNav = "cLevel"
    Temperature = "Temp"
    WindSpeed = "Wspd"
    WindGust = "MaxWspd"
    WindDir = "Wdir"


WATER_PARAMS = [Param.LevelNav, Param.CorrectedLevelNav, Param.Temperature]
WIND_PARAMS = [Param.WindSpeed, Param.WindGust, Param.WindDir]

"""
Access CDMO web services to retrieve observed tide, wind, and temperature data. 
"""

logger = logging.getLogger(__name__)
_max_wind_speed = 120  # max sane wind speed in mph


def get_water_data(station: Station, timeline: Timeline, useDb: bool = True) -> Tides:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Paramters:
    station (Station): the station object
    timeline (Timeline): the timeline of datetimes to fetch data for
    useDb: use database instead of calling API; can be overridden with FORCE_API_CDMO env setting

    Returns:
    {dt: {"level": <value>, "temp": <value>}}
    """
    tides = Tides(mllw_offset=station.mllw_conversion)

    if timeline.is_all_future():
        return tides

    force_api = os.environ.get("FORCE_API_CDMO", "0") == "1"
    if force_api:
        logger.warning("Forced to use API for CDMO data!")

    if useDb and not force_api:
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
            station=get_station(station.id), time__range=(start_param, end_param)
        ).order_by("time")
        logger.debug(
            f"Found {queryset.count()} rows in db for {station.id} from {start_dt} to {end_dt}"
        )
        for rec in queryset:
            in_utc = datetime.fromisoformat(rec.time)
            dt_in_local = in_utc.astimezone(timeline.time_zone)
            tides.add_feet(
                dt=dt_in_local,
                temp_f=rec.temp,
                mllw_feet=rec.level,
                corrected_nav_feet=rec.clevel_nf,
            )

    else:
        logger.debug(
            f"station.id={station.id} pulling {WATER_PARAMS} for {timeline.start_dt} to {timeline.end_dt} from cdmo"
        )
        tides = get_cdmo_tide(timeline, station, WATER_PARAMS)
        tides.sort()  # It's handy to have keys in chrono order, not reverse order

        logger.debug(f"Total raw water data points: {tides.length}")

    return tides


def get_wind_data(station: Station, timeline: Timeline, useDb: bool = True) -> Winds:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Args:
    station (Station): the station object
    timeline (Timeline): the timeline of datetimes to fetch data for
    useDb: use database instead of calling API; can be overridden with FORCE_API_CDMO env setting

    Returns:
    - Winds object, which may contain no data.
    """

    winds = Winds()

    # If timeline is all in the future, don't bother.
    if timeline.is_all_future():
        return winds

    force_api = os.environ.get("FORCE_API_CDMO", "0") == "1"
    if force_api:
        logger.warning("Forced to use API for CDMO data!")

    if useDb and not force_api:
        use_padding = isinstance(timeline, GraphTimeline)
        start_dt = timeline.get_min(use_padding)
        end_dt = timeline.get_max(use_padding)

        # query must pass datetimes as strings in ISO format: "2024-01-01T05:30:00+00:00"
        start_param = start_dt.astimezone(tz.utc).isoformat()
        end_param = end_dt.astimezone(tz.utc).isoformat()

        queryset = Wind.objects.filter(
            station=get_station(station.id), time__range=(start_param, end_param)
        ).order_by("time")
        logger.debug(
            f"Found {queryset.count()} rows in db for {station.id} from {start_dt} to {end_dt}"
        )
        for rec in queryset:
            in_utc = datetime.fromisoformat(rec.time)
            dt_in_local = in_utc.astimezone(timeline.time_zone)

            winds.add(
                dt=dt_in_local,
                speed_mph=rec.speed,
                gust_mph=rec.gust,
                direction_deg=rec.dir_deg,
            )

    else:
        logger.debug(
            f"station.id={station.id} pulling {WIND_PARAMS} for {timeline.start_dt} to {timeline.end_dt} from cdmo"
        )
        winds = get_cdmo_wind(timeline, station)
        logger.debug(f"Total raw wind data points: {winds.length}")

    return winds


def get_cdmo_tide(timeline: Timeline, station: Station, params: list) -> Tides:
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
    - Tides object, which may contain no data.

    """
    if station is None:
        raise util.InternalError("station is required")

    # validate that timeline datetimes are on 15-minute intervals and seconds=0
    if timeline.start_dt.minute % 15 > 0 or timeline.start_dt.second > 0:
        # CDMO data is always on 15-minute intervals.
        raise util.InternalError("datetimes must be on 15-minute intervals")

    xml = get_cdmo_xml(timeline, station, params)
    return parse_cdmo_tides_xml(timeline, station, xml)


def get_cdmo_wind(timeline: Timeline, station: Station) -> Winds:
    """
    Get XML data from CDMO, parse it, convert to requested timezone.
    As of Feb 2024, these CDMO endpoints will return a maximum of 1000 data points. At 96 points per day (4 per hour),
    that's about 10.5 days. Therefore, no more than 10 days should be requested.  If you ask for more, CDMO truncates
    data points starting from the oldest data, not the latest.  So care should be taken not to ask for too much,
    else data at the beginning of the graph will be missing.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the swmp station object

    Returns:
    - Winds object, which may contain no data.

    """
    if station is None:
        raise util.InternalError("station is required")

    # validate that timeline datetimes are on 15-minute intervals and seconds=0
    if timeline.start_dt.minute % 15 > 0 or timeline.start_dt.second > 0:
        # CDMO data is always on 15-minute intervals.
        raise util.InternalError("datetimes must be on 15-minute intervals")

    xml = get_cdmo_xml(timeline, station, WIND_PARAMS)
    return parse_cdmo_wind_xml(timeline, xml)


def get_cdmo_xml(timeline: Timeline, station: Station, params: list) -> str:
    """
    Retrieve CDMO data as requested. Returns the xml returned from CDMO as a string.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the swmp station object
    - params: list of requested CDMO parameters

    Returns:
    - XML as string
    """
    # Because CDMO returns units of entire days using LST, we may need to adjust the dates we request.
    # When getting Level data, we add padding before and after to help determine highs/lows when they are near the boundaries.
    use_padding = Param.LevelNav in params and isinstance(timeline, GraphTimeline)

    req_start_date, req_end_date = compute_cdmo_request_dates(
        timeline.get_min(use_padding), timeline.get_max(use_padding)
    )

    data_station_id = (
        station.id if Param.LevelNav in params else station.weather_station_id
    )

    try:
        logger.debug(f"Calling CDMO for {params} {req_start_date} to {req_end_date}")
        param_str = ",".join(p.value for p in params)
        xml = SoapClient.get_client().service.exportAllParamsDateRangeXMLNew(
            data_station_id, req_start_date, req_end_date, param_str
        )
        return xml

    except Exception as e:
        logger.error(
            f"{type(e)} getting {param_str} data {req_start_date} to {req_end_date} from CDMO: {e}",
            stack_info=False,
        )
        raise APIException()


def parse_cdmo_tides_xml(timeline: Timeline, station: Station, xml: str) -> Tides:
    """
    Parse the data returned from CDMO for the requested timeline.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the swmp station object
    - xml: tide data xml from cdmo

    Returns:
    - Tides object, which may contain no data.

    """
    tides = Tides(mllw_offset=station.mllw_conversion)

    if xml is None or len(xml) == 0:
        return tides

    # We need to pull data for the padded timeline, for hi/lo functionality, not just
    # display times. No sense looking for future, these are observations. If asking for
    # tide level, we need a padded timeline to identify highs and lows that are near the edges of the timeline.
    past_timeline = timeline.get_all_past(padded=isinstance(timeline, GraphTimeline))

    root = ElTree.fromstring(xml)  # ElementTree.Element
    text_error_check(root)
    records = ignored = none_or_bad = 0
    for reading in root.findall(".//data"):  # use XPATH to dig out our data points
        records += 1
        # we use utcStamp, not the DateTimeStamp because the latter is in LST, not sensitive to DST.
        try:
            date_str = reading.find("./utcStamp").text
            dt_in_local = (
                datetime.strptime(date_str, "%m/%d/%Y %H:%M")
                .replace(tzinfo=tz.utc)
                .astimezone(timeline.time_zone)
            )
        except ValueError:
            none_or_bad += 1
            logger.error("Skipping bad datetime '%s'", date_str)
            continue

        # Since we query more data than we need, only save the data that is in the requested timeline.
        # For GraphTimeline's, this includes any padded times for hi/lo functionality.
        if dt_in_local not in past_timeline:
            ignored += 1
            continue

        # Extract and convert all the params we're looking for.
        temp_c = handle_float(reading, Param.Temperature.value, False, dt_in_local)
        level_nav_meters = handle_float(
            reading, Param.LevelNav.value, True, dt_in_local
        )
        if level_nav_meters is None:
            none_or_bad += 1
            continue

        corrected_level_nav_meters = handle_float(
            reading,
            Param.CorrectedLevelNav.value,
            True,
            dt_in_local,
        )
        if corrected_level_nav_meters is None:
            none_or_bad += 1
            continue

        tides.add_meters(
            dt=dt_in_local,
            temp_c=temp_c,
            nav_meters=level_nav_meters,
            corrected_nav_meters=corrected_level_nav_meters,
        )

    if none_or_bad > 0:
        logger.warning(
            f"parse_cdmo_tide_xml: {none_or_bad} of {records - ignored} expected records had missing or invalid data"
        )
    return tides


def parse_cdmo_wind_xml(timeline: Timeline, xml: str) -> Winds:
    """
    Parse the wind data returned from CDMO for the requested timeline.

    Parameters:
    - timeline: list of datetime representing what will be displayed on the graph
    - xml: wind data xml from cdmo

    Returns:
    - Winds object, which may contain no data.

    """
    winds = Winds()

    if xml is None or len(xml) == 0:
        return winds

    past_timeline = timeline.get_all_past(False)

    root = ElTree.fromstring(xml)  # ElementTree.Element
    text_error_check(root)
    records = ignored = none_or_bad = 0
    for reading in root.findall(".//data"):  # use XPATH to dig out our data points
        records += 1
        # we use utcStamp, not the DateTimeStamp because the latter is in LST, not sensitive to DST.
        try:
            date_str = reading.find("./utcStamp").text
            dt_in_local = (
                datetime.strptime(date_str, "%m/%d/%Y %H:%M")
                .replace(tzinfo=tz.utc)
                .astimezone(timeline.time_zone)
            )
        except ValueError:
            none_or_bad += 1
            logger.error("Skipping bad datetime '%s'", date_str)
            continue

        # Since we query more data than we need, only save the data that is in the requested timeline.
        if dt_in_local not in past_timeline:
            ignored += 1
            continue

        # Extract and convert all the params we're looking for.
        wind_speed_mph = handle_windspeed(reading, Param.WindSpeed.value, dt_in_local)
        wind_gust_mph = handle_windspeed(reading, Param.WindGust.value, dt_in_local)
        wind_direction_deg = handle_wind_degrees(
            reading, Param.WindDir.value, dt_in_local
        )
        if (
            wind_speed_mph is None
            or wind_gust_mph is None
            or wind_direction_deg is None
        ):
            none_or_bad += 1
            continue

        winds.add(
            dt=dt_in_local,
            speed_mph=wind_speed_mph,
            gust_mph=wind_gust_mph,
            direction_deg=wind_direction_deg,
        )

    if none_or_bad > 0:
        logger.warning(
            f"{none_or_bad} of {records - ignored} expected records had missing or invalid data"
        )
    return winds


def text_error_check(rootElement):
    """If a node is not supposed to have text, return that text, else None
    This is how CDMO returns an error e.g. Invalid IP address.
    """
    data_node = rootElement.find(".//data")
    try:
        message = data_node.text.strip()
        if len(message) > 0:
            logger.error("Received unexpected message from CDMO: %s", message)
            raise APIException(f"CDMO returned: {message}")
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
    timeline: GraphTimeline, tides: Tides, astro_pred_dict: dict
) -> dict:
    """
    Build a dense dict of high and low tides times from observed and predicted tide data.  For the part the
    timeline in the future, it will just use the provided PredictedHighOrLow as is. For the part of the
    timeline in the past, it will try to discover the observed highs and lows, using the predicted values
    as a guide. Ideally we are able to identify them, and if we do, they will be returned as ObservedHighOrLow.
    But in the rare case where there is missing observed data such that it's impossible to accurately identify
    the high or low, we'll use the *predicted* high/low -- a PredictedHighOrLow instead. This allows graphs
    to display an accurate, labeled High/Low prediction value for parts of the timeline in the past, where
    normally only the Observed tide plot would display and label its highs/lows.  The idea being is that it's
    better to label the predicted high/low than have no high/low labled at all.

    Args:
    - timeline: key-ordered Timeline of datetimes for the graph. May be any combination of past/future.
    - obs_dict: dense dict of observed tide readings {datetime: {"level": val, "temp": val"}}
    - astro_pred_dict: dense dict of predicted high and low tides covering the entire timeline.
        {timeline_dt: PredictedHighOrLow}

    Returns:
        sparse dict of {dt: <HighOrLow subclass>} best information on all high or low tides in timeline
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
        observed = {t: tides.getTide(t) for t in candidate_times}
        # remove the times which have no tide data
        observed = {k: v for k, v in observed.items() if v is not None}
        if len(observed) > 0:
            if pred.hilo == Hilo.HIGH:
                observed_hilo_dt = max(
                    observed.items(), key=lambda tup: tup[1].corrected_mllw_feet
                )[0]
            else:
                observed_hilo_dt = min(
                    observed.items(), key=lambda tup: tup[1].corrected_mllw_feet
                )[0]
            hilomap[observed_hilo_dt] = ObservedHighOrLow(
                observed[observed_hilo_dt].corrected_mllw_feet, pred.hilo
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


def handle_float(element, fieldName: str, required: bool, local_dt: datetime):
    try:
        data_str = None
        data_str = element.find(f"./{fieldName}").text
        float_val = float(data_str)
        if float_val is None and required:
            raise ValueError()
        return float_val
    except:
        logger.debug(
            "Invalid or missing %s for %s: '%s'", fieldName, local_dt, data_str
        )
        return None


def handle_windspeed(element, fieldName: str, local_dt: datetime):
    """Convert wind speed string in meters per sec to miles per hour. Returns None if missing or bad data."""
    try:
        wspd_str = "?"
        wspd_str = element.find(f"./{fieldName}").text
        if wspd_str is None or len(wspd_str.strip()) == 0:
            raise ValueError()
        meters_per_sec = float(wspd_str)
        mph = util.meters_per_second_to_mph(meters_per_sec)
        if mph < 0 or mph > _max_wind_speed:
            raise ValueError()
        return mph
    except:
        logger.debug("invalid or missing %s: '%s' at %s", fieldName, wspd_str, local_dt)
        return None


def handle_wind_degrees(element, fieldName: str, local_dt: datetime):
    """Convert wind direction string to degrees. Returns None if missing or bad data."""
    try:
        deg_str = "?"
        deg_str = element.find(f"./{fieldName}").text
        if deg_str is None or len(deg_str.strip()) == 0:
            raise ValueError()
        degrees = int(deg_str)
        if degrees < 0 or degrees > 360:
            raise ValueError()
        return degrees
    except:
        logger.debug("invalid or missing %s: '%s' at %s", fieldName, deg_str, local_dt)
        return None
