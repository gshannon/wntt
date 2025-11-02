import logging
import os
import xml.etree.ElementTree as ElTree
from datetime import date, datetime, timedelta

from app import tzutil as tz
from app import util
from app.datasource.custom_transport import CustomTransport
from app.timeline import Timeline
from rest_framework.exceptions import APIException
from suds.client import Client

"""
Utility data and functions for graph building. 
"""

logger = logging.getLogger(__name__)
cdmo_wsdl = "https://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl"
windspeed_param = "Wspd"
windgust_param = "MaxWspd"
winddir_param = "Wdir"
tide_param = "Level"
temp_param = "Temp"
min_tide = -2.0  # any mllw/feet tide reading lower than this is considered bad data
max_tide = 20.0  # any mllw/feet tide reading higher than this is considered bad data
max_wind_speed = 120  # any wind speed reading higher than this is considered bad data

# this is a temp workaround to an issue where recreating the suds client on
# every request is causing the user/password to be rejected by CDMO. This should be
# cleaned up once that issue is resolved.
_client = None


def get_soap_client():
    global _client
    if not _client:
        user_name = os.environ.get("CDMO_USER")
        password = os.environ.get("CDMO_PASSWORD")
        transport = CustomTransport(user_name, password)
        _client = Client(cdmo_wsdl, timeout=90, retxml=True, transport=transport)
    return _client


def get_recorded_tides(timeline: Timeline, **kwargs) -> dict:
    """Retrieve tide water levels from CDMO relative to MLLW feet.

    Args:
        timeline (Timeline): the timeline of datetimes to fetch data for
        **kwargs: Should contain water_station & noaa_station_id. Needs to be kwargs
          so this method can be called in parallel.

    Returns:
        dict: dense dict, {dt: level} where dt is a datetime in the timeline and level is the
        tide level in MLLW feet.
    """
    if timeline.is_all_future():
        # Nothing to fetch
        return {}

    water_station = kwargs.pop("water_station")
    noaa_station_id = kwargs.pop("noaa_station_id")
    # Note that CDMO records water level in meters relative to NAVD88, so we use a converter.
    return get_cdmo(
        timeline,
        water_station,
        tide_param,
        converter=make_navd88_level_converter(noaa_station_id),
    )


def get_recorded_wind_data(timeline: Timeline, **kwargs) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.

    Args:
        timeline (Timeline): the timeline of datetimes to fetch data for
        **kwargs: Should contain weather_station. Needs to be kwargs so this method can be called in parallel.

    Returns:
        dense dict of {dt: {speed, gust, dir, dir_str}}
    """

    weather_station = kwargs.pop("weather_station")

    wind_dict = {}

    # If timeline is all in the future, don't bother.
    if timeline.is_all_future():
        return wind_dict

    speed_dict = get_cdmo(timeline, weather_station, windspeed_param, handle_windspeed)
    logger.debug(f"Wind speed data points retrieved: {len(speed_dict)}")

    if len(speed_dict) == 0:
        return wind_dict

    # CDMO returns wind speed in meters per second, so convert to mph.
    gust_dict = get_cdmo(timeline, weather_station, windgust_param, handle_windspeed)
    logger.debug(f"Wind gust data points retrieved: {len(gust_dict)}")
    dir_dict = get_cdmo(timeline, weather_station, winddir_param, lambda d, dt: int(d))
    logger.debug(f"Wind direction data points retrieved: {len(dir_dict)}")

    # Assemble all the data.
    # The graph will display compass point names, so translate the direction into strings for dir_str.
    for dt, speed in speed_dict.items():
        # Make sure we have all values, or none.
        if dt not in gust_dict or dt not in dir_dict:
            logger.error(f"Missing gust and/or direction wind data for {dt}")
            continue
        wind_dict[dt] = {
            "speed": speed,
            "gust": gust_dict[dt],
            "dir": dir_dict[dt],
            "dir_str": (
                util.degrees_to_dir(dir_dict[dt]) if dir_dict[dt] is not None else None
            ),
        }

    return wind_dict


def get_recorded_temps(timeline: Timeline, water_station: str) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of water temp readings from CDMO.
    """
    if timeline.is_all_future():
        # Nothing to fetch, it's all in the future
        return None

    # Use a converter to convert from string to formatted number.
    return get_cdmo(timeline, water_station, temp_param, converter=handle_float)


def get_cdmo(timeline: Timeline, station: str, param: str, converter) -> dict:
    """
    Get XML data from CDMO, parse it, convert to requested timezone.
    Returns a dense dict of tide levels, key = dt, value = level

    Parameters:
    timeline : datetimes (tz aware) requested by the user, in ordered 15-minute intervals
    station : name of the station that is the data source
    param : name of the data parameter being requested
    converter : a function to convert a data point into the desired type, e.g. float or int, or unit conversion

    As of Feb 2024, these CDMO endpoints will return a maximum of 1000 data points. At 96 points per day (4 per hour),
    that's about 10.5 days. Therefore, no more than 10 days should be requested.  If you ask for more, CDMO truncates
    data points starting from the MOST RECENT data, not the latest.  So care should be taken not to ask for too much,
    else data at the beginning of the graph will be missing.

    CDMO returns dates in LST (local standard time), which is not sensitive to DST.
    """
    xml = get_cdmo_xml(timeline, station, param)
    data = get_cdmo_data(timeline, xml, param, converter)
    return data


def get_cdmo_xml(timeline: Timeline, station: str, param: str) -> dict:
    """
    Retrieve CDMO data as requested. Returns the xml returned from CDMO as a string.
    Params:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the CDMO station code
    - param: the CDMO param code
    """
    # Because CDMO returns units of entire days using LST, we may need to adjust the dates we request.
    # Note we add padding before and after to help determine highs/lows when they are near the boundaries.
    req_start_date, req_end_date = compute_cdmo_request_dates(
        timeline.get_min_with_padding(), timeline.get_max_with_padding()
    )

    # soap_client = Client(cdmo_wsdl, timeout=90, retxml=True, transport=get_transport())

    try:
        client = get_soap_client()
        xml = client.service.exportAllParamsDateRangeXMLNew(
            station, req_start_date, req_end_date, param
        )
        # util.dump_xml(xml, f"/surgedata/{param}-cdmo.xml")
    except Exception as e:
        logger.error(
            f"Error getting {param} data {req_start_date} to {req_end_date} from CDMO",
            exc_info=e,
        )
        raise APIException()

    logger.debug(
        f"CDMO {param} data retrieved for {station} for {req_start_date} to {req_end_date}"
    )
    return xml


def get_cdmo_data(timeline: Timeline, xml: str, param: str, converter) -> dict:
    """
    Parse the data returned from CDMO for the requested timeline. Returns a dense, key-ordered
    dict of {dt: value} where dt=datetime matching an element of the timeline and value = the data value.
    Params:
    - timeline: list of datetime representing what will be displayed on the graph
    - xml: string with the contents in XML format
    - param: the CDMO param code
    - converter: func to convert raw data to desired display value
    - minutes of each hour to include. XML will contain an entry for every 15 minutes
    """
    datadict = {}  # {dt: value}
    if xml is None or len(xml) == 0:
        return datadict

    # We need to pull data for the padded timeline, for hi/lo functionality, not just
    # display times. No sense looking for future, these are observations.
    padded_timeline = timeline.get_all_past()

    root = ElTree.fromstring(xml)  # ElementTree.Element
    text_error_check(root.find(".//data"))
    records = skipped = nodata = 0
    for reading in root.findall(".//data"):  # use XPATH to dig out our data points
        records += 1
        # we use the utc stamp, not the DateTimeStamp because the latter is in LST, sensitive to DST.
        date_str = reading.find("./utcStamp").text
        try:
            naive_utc = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        except ValueError:
            logger.error(f"Skipping bad datetime '{date_str}'")
            continue

        # We need this local time. First promote to UTC.
        in_utc = naive_utc.replace(tzinfo=tz.utc)
        # Now convert to requested tzone, so DST is handled properly
        dt_in_local = in_utc.astimezone(timeline.time_zone)
        # Since we query more data than we need, only save the data that is in the requested timeline.
        if dt_in_local not in padded_timeline:
            skipped += 1
            continue
        data_str = reading.find(f"./{param}").text
        try:
            value = converter(data_str, dt_in_local)
            if value is None:
                nodata += 1
            else:
                datadict[dt_in_local] = value
        except (TypeError, ValueError):
            logger.error(f"Invalid {param} for {naive_utc}: '{data_str}'")

    logger.debug(f"read={records} skipped={skipped} nodata={nodata}")

    if len(datadict) == 0:
        logger.warning(f"Got no {param} data from {records} records read")

    # XML data is returned in reverse chronological order. Reverse it here.
    return dict(reversed(list(datadict.items())))


def text_error_check(non_text_node):
    """If a node is not supposed to have text, return that text, else None
    This is how CDMO returns an error e.g. Invalid IP address.
    """
    try:
        message = non_text_node.text.strip()
        if len(message) > 0:
            logger.error(f"Received unexpected message from CDMO: {message}")
            raise APIException(message)
    except AttributeError:
        pass


def compute_cdmo_request_dates(
    start_time: datetime, end_time: datetime
) -> tuple[date, date]:
    """
    CDMO will give us only full days of data, using LST of the time zone of the requesting station. It
    does not honor DST. So we may have to adjust the start date and/or the end date, to avoid missing data
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


def find_hilos(timeline: Timeline, obs_dict: dict) -> dict:
    """Given a key-ordered timeline and dense dict of tide readings {datetime: level}, return a dense dict of
    {dt: 'H' or 'L'} indicating which of the datetimes correspond to a high or low tide. We only return
    datetimes that are definitively high or low tides, and do not include any that are ambiguous.

    In this function, an "arc" is a series of consecutive tide readings which may may contain a high or low
    tide. Values above the mid-tide level are a potential high tide arc, and below it, a low tide arc.
    We take the max/min value from each arc to look for the high/low tide.  Mid-tide is defined
    as the average of the highest and lowest value seen in the data, with a minimum allowable
    value in case of lots of missing data. Since we may have missing data for some datetimes, in which
    case the value will be None, we take a conservative approach and prefer false negatives (not
    identifying a high or low tide) to false positives (identifying a high or low tide that is not
    necessarily one).

    We are expecting a timeline with full days, at 96 per day, so whether we are dealing with a diurnal
    or semidiurnal station, there should be at least 1 high and 1 low per day.  Peaks and troughs are
    identified by consecutive values like [9.5, 10.1, 9.9] and [2.5, 2.1, 2.1, 2.1, 2.3]. Up to 4 missing
    values will be tolerated, so [7, 8, None, None, None, None, 7] would yield a peak of 8.  More than 4
    will cause the arced to be skipped for fear they are disguising the actual peak or trough.
    """

    # In feet. If range is less than this, there's likely a lot of missing data.
    MIN_TIDAL_RANGE = 4
    (HIGH_ARC, LOW_ARC) = ("H", "L")
    hilomap = {}  # {dt: 'H' or 'L'}

    if len(obs_dict) == 0:
        return hilomap  # nothing to do

    padded_timeline = timeline.get_all_past()

    highest = max(obs_dict.values())
    lowest = min(obs_dict.values())
    if highest - lowest < MIN_TIDAL_RANGE:
        # This could happen if the equipment malfunctions for a long period of time.
        logger.warning(
            f"Tidal range too small: {highest - lowest}, high={highest} low={lowest}"
        )
        return hilomap

    midtide = round((highest + lowest) / 2, 1)
    logger.debug(f"hi={highest} low={lowest} midtide={midtide} points={len(obs_dict)}")

    # Phase 1: Walk through the timeline and identify arcs.  An arc is a half-cycle of the wave --
    # above or below the midline -- each of which may contain a high or low tide.
    arcs = []  # [{position: H/L, datadict: {dt: level}}]  datadict is dense and key-ordered

    cur_arc = None
    for dt in padded_timeline:
        val = obs_dict.get(dt, None)
        if val is not None:
            position = HIGH_ARC if val > midtide else LOW_ARC
            if cur_arc is None:
                cur_arc = {"position": position, "datadict": {dt: val}}
            else:
                if cur_arc["position"] != position:
                    # We've moved across the mid line. Save the arc we were working on.
                    arcs.append(cur_arc)
                    cur_arc = {"position": position, "datadict": {dt: val}}
                else:
                    cur_arc["datadict"][dt] = val

    arcs.append(cur_arc)  # save the last one we were working on

    # Phase 2: Walk through arcs and look for valid ones.
    for arc in arcs:
        position = arc["position"]
        datadict = arc["datadict"]
        logger.debug(
            f"Arc pos={position} values={len(datadict)} timedelta={max(datadict) - min(datadict)} "
        )

        # The shortest possible peak or trough is 3 consecutive data points, e.g. [8,9,8], with the rest Nones.
        if len(datadict) < 3:
            continue

        hilo_dt = (
            max(datadict, key=datadict.get)
            if position == HIGH_ARC
            else min(datadict, key=datadict.get)
        )
        hilo_val = datadict.get(hilo_dt)

        arc_timeline = list(
            filter(
                lambda dt: min(datadict) <= dt <= max(datadict),
                padded_timeline,
            )
        )
        sparse_vals = [datadict.get(dt, None) for dt in arc_timeline]
        # The first and last values are not candidates for high or low tide, since there's no value on the other
        # side to prove it.
        if sparse_vals[0] == hilo_val or sparse_vals[-1] == hilo_val:
            logger.debug(
                f"hi/lo {hilo_val} found at beginning or end of arc beginning at {arc_timeline[0]}"
            )
            continue
        # We need to see a peak or trough with no None's breaking it up. E.g. [7,8,7] or [3,2,2,3] Not [7,8,None,7]
        ndx = sparse_vals.index(hilo_val)  # returns the 1st instance of the high/low.
        if sparse_vals[ndx - 1] is None:
            logger.debug(
                f"None found before hi/lo {hilo_val} in arc beginning at {arc_timeline[0]}"
            )
            continue
        # Finally check the right side. Any number of repeats are allowed, but must end with a different value.
        accepted = False
        nonesSkipped = 0
        for val in sparse_vals[ndx + 1 :]:
            if val is None:
                logger.debug(
                    f"None found after {hilo_val} in arc beginning at {arc_timeline[0]}"
                )
                # We'll allow up to 4 None's.
                nonesSkipped += 1
                if nonesSkipped > 4:
                    break
            elif val != hilo_val:
                accepted = True
                break

        if accepted:
            logger.debug(f"Accepted as {position}: {hilo_dt} - {hilo_val} ft")
            hilomap[hilo_dt] = position

    return hilomap


def handle_float(data_str: str, local_dt: datetime):
    """Convert string to float. Returns None if bad data."""
    if data_str is None or len(data_str.strip()) == 0:
        return None
    try:
        value = float(data_str)
    except ValueError:
        logger.error(f"Invalid float for {local_dt}: '{data_str}'")
        value = None
    return value


def make_navd88_level_converter(noaa_station_id: str):
    """Make a lambda to convert navd88 to mllw for a particular station."""
    return lambda level_str, local_dt: handle_navd88_level(
        level_str, local_dt, noaa_station_id
    )


def handle_navd88_level(level_str: str, local_dt: datetime, noaa_station_id: str):
    """Convert tide string in navd88 meters to MLLW feet. Returns None if bad data."""
    if level_str is None or len(level_str.strip()) == 0:
        logger.warning(f"skipping [{level_str}]")
        return None
    try:
        read_level = float(level_str)
        level = util.navd88_meters_to_mllw_feet(read_level, noaa_station_id)
        if level < min_tide or level > max_tide:
            logger.error(
                f"level out of range for {local_dt}: {level} (raw: {read_level})"
            )
            level = None
    except ValueError:
        logger.error(f"invalid level: [{level_str}]")
        level = None
    return level


def handle_windspeed(wspd_str: str, local_dt: datetime):
    """Convert wind speed string in meters per sec to miles per hour. Returns None if bad data."""
    if wspd_str is None or len(wspd_str.strip()) == 0:
        return None
    try:
        read_wspd = float(wspd_str)
        mph = util.meters_per_second_to_mph(read_wspd)
        if mph < 0 or mph > max_wind_speed:
            logger.error(
                f"wind speed out of range for {local_dt}: {read_wspd} mps converted to {mph} mph"
            )
            mph = None
    except ValueError:
        logger.error(f"invalid windspeed: [{wspd_str}]")
        mph = None
    return mph


def dump_all_codes():
    """Utility function to dump all NERRS metadata to a file."""
    soap_client = Client(cdmo_wsdl, timeout=90, retxml=True)
    try:
        xml = soap_client.service.exportStationCodesXMLNew()
        util.dump_xml(xml, "/surgedata/StationCodes.xml")
    except Exception as e:
        logger.error("Error getting all codes from CDMO", exc_info=e)
        raise APIException()
    root = ElTree.fromstring(xml)  # ElementTree.Element
    return root
