import logging
import xml.etree.ElementTree as ElTree
from datetime import date, datetime, time, timedelta

from rest_framework.exceptions import APIException
from suds.client import Client

from app import tzutil as tz
from app import util

"""
Utility data and functions for graph building. 
"""

logger = logging.getLogger(__name__)
cdmo_wsdl = "https://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl"
wells_water_station = "welinwq"
wells_met_station = "wellfmet"
windspeed_param = "Wspd"
windgust_param = "MaxWspd"
winddir_param = "Wdir"
tide_param = "Level"
temp_param = "Temp"
min_tide = -2.0  # any mllw/feet tide reading lower than this is considered bad data
max_tide = 20.0  # any mllw/feet tide reading higher than this is considered bad data
max_wind_speed = 120  # any wind speed reading higher than this is considered bad data


def get_recorded_tides(
    timeline: list, station=wells_water_station, param=tide_param, dump=False
) -> dict:
    """
    For the given timeline, get a dense dict of tide water levels from CDMO in MLLW feet.
    """

    if timeline[0] > tz.now(timeline[0].tzinfo):
        # Nothing to fetch, it's all in the future
        return {}

    return get_cdmo(timeline, station, param, converter=handle_navd88_level, dump=True)


def get_recorded_wind_data(timeline: list) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of data from CDMO.
    """

    datadict = {}  # {dt: {speed, gust, dir, dir_str}}

    # If this is for the future, don't bother.
    if timeline[0].date() > tz.now(timeline[0].tzinfo).date():
        return datadict

    # For readability, thin out the data points, as it gets pretty dense and hard to read.
    days = (timeline[-1].date() - timeline[0].date()).days
    if days > 5:
        minutes = [0]  # only show 1 point per hour
    elif days > 2:
        minutes = [0, 30]  # show 2 per hour
    else:
        minutes = [0, 15, 30, 45]  # show all 4

    speed_dict = get_cdmo(
        timeline, wells_met_station, windspeed_param, handle_windspeed, minutes
    )
    # HACK. In the unlikely case there are no speed data points at all (all None), we have chosen to display
    # an empty graph. However, there's a quirk in plotly express where it crashes if all data points are None.
    # So we cheat and add a single all-zero entry.
    if len(speed_dict) == 0:
        datadict[timeline[0]] = {
            "speed": 0,
            "gust": 0,
            "dir": 0,
            "dir_str": util.degrees_to_dir(0),
        }
        return datadict

    gust_dict = get_cdmo(
        timeline, wells_met_station, windgust_param, handle_windspeed, minutes
    )
    dir_dict = get_cdmo(
        timeline, wells_met_station, winddir_param, lambda d, dt: int(d), minutes
    )

    # Plotly can't handle a None in the wind direction data, so if there are any, we must set the speed
    # values to None also so plotly just skips the data point.
    for key, val in dir_dict.items():
        if val is None:
            logger.error(f"Found None wind dir for {key}")
            speed_dict[key] = gust_dict[key] = None

    # Assemble all the data.
    # The graph will display compass point names, so translate the direction into strings for dir_str.
    for key, val in speed_dict.items():
        if key not in gust_dict or key not in dir_dict:
            logger.error(f"Missing gust and/or direction wind data for {key}")
            continue
        datadict[key] = {
            "speed": val,
            "gust": gust_dict[key],
            "dir": dir_dict[key],
            "dir_str": (
                util.degrees_to_dir(dir_dict[key])
                if dir_dict[key] is not None
                else None
            ),
        }

    return datadict


def get_recorded_temps(timeline: list, station=wells_water_station) -> dict:
    """
    For the given list of timezone-aware datetimes, get a dense dict of water temp readings from CDMO.
    """
    if timeline[0] > tz.now(timeline[0].tzinfo):
        # Nothing to fetch, it's all in the future
        return None

    return get_cdmo(timeline, station=station, param=temp_param, converter=handle_float)


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


def get_cdmo(
    timeline: list,
    station: str,
    param: str,
    converter,
    included_minutes=[0, 15, 30, 45],
    dump=False,
) -> dict:
    """
    Get XML data from CDMO, parse it, convert to requested timezone.
    Returns a dense dict of tide levels, key = dt, value = level

    Parameters:
    timeline : datetimes (tz aware) requested by the user, in ordered 15-minute intervals
    station : name of the station that is the data source
    param : name of the data parameter being requested
    converter : a function to convert a data point into the desired type, e.g. float or int, or unit conversion
    included_minutes : subset of [0,15,30,45] to indicate which data points to populate in each hour. Giving a subset
        allows you to display a sparser graph.

    As of Feb 2024, these CDMO endpoints will return a maximum of 1000 data points. At 96 points per day (4 per hour),
    that's about 10.5 days. Therefore, no more than 10 days should be requested.  If you ask for more, CDMO truncates
    data points starting from the MOST RECENT data, not the latest.  So care should be taken not to ask for too much,
    else data at the beginning of the graph will be missing.

    CDMO returns dates in LST (local standard time), which is not sensitive to DST.
    """
    logger.debug(f"station={station}, param={param} dump={dump}")
    xml = get_cdmo_xml(timeline, station, param, dump)
    data = get_cdmo_data(timeline, xml, param, converter, included_minutes)
    return data


def get_cdmo_xml(
    timeline: list,
    station: str,
    param: str,
    dump=False,
) -> dict:
    """
    Retrieve CDMO data as requested. Returns the xml returned from CDMO as a string.
    Params:
    - timeline: list of datetime representing what will be displayed on the graph
    - station: the CDMO station code
    - param: the CDMO param code
    - dump: for debugging
    """
    # Because CDMO returns units of entire days using LST, we may need to adjust the dates we request.
    req_start_date, req_end_date = compute_cdmo_request_dates(timeline)
    soap_client = Client(cdmo_wsdl, timeout=90, retxml=True)

    try:
        xml = soap_client.service.exportAllParamsDateRangeXMLNew(
            station, req_start_date, req_end_date, param
        )
        if dump:
            util.dump_xml(xml, f"/surgedata/{param}-cdmo.xml")
    except Exception as e:
        logger.error(
            f"Error getting {param} data {req_start_date} to {req_end_date} from CDMO",
            exc_info=e,
        )
        raise APIException()

    return xml


def get_cdmo_data(
    timeline: list,
    xml: str,
    param: str,
    converter,
    included_minutes: list = [0, 15, 30, 45],
) -> dict:
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
    # Build a dict with key=datetime of the xml data, and val=the read value
    datadict = {}  # {dt: value}
    if xml is None or len(xml) == 0:
        return datadict

    root = ElTree.fromstring(xml)  # ElementTree.Element
    text_error_check(root.find(".//data"))
    records = skipped = skipmin = nodata = 0
    for reading in root.findall(".//data"):  # use XPATH to dig out our data points
        records += 1
        # we use the utc stamp, not the DateTimeStamp because it is a local time that is not sensitive to DST.
        date_str = reading.find("./utcStamp").text
        try:
            naive_utc = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        except ValueError:
            logger.error(f"Skipping bad datetime '{date_str}'")
            continue
        if naive_utc.minute in included_minutes:
            # We need this local time. First promote to UTC.
            in_utc = naive_utc.replace(tzinfo=tz.utc)
            # Now convert to requested tzone, so DST is handled properly
            dt_in_local = in_utc.astimezone(timeline[0].tzinfo)
            # Since we query more data than we need, only save the data that is in the requested timeline.
            if dt_in_local not in timeline:
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
        else:
            skipmin += 1

    logger.debug(f"read={records} skipped={skipped} nodata={nodata} skipmin={skipmin}")

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


def compute_cdmo_request_dates(timeline: list) -> tuple[date, date]:
    """
    CDMO will give us only full days of data, using LST of the time zone of the requesting station. It
    does not honor DST. So if the start date at 00:00 is not in DST, then there's no problem. Otherwise, since all
    US timezones are behind UTC, we need to ask for the previous day as well, so we get what CDMO thinks is the
    last hour of the previous day, which is actually the first hour of the requested start date.

    Additionally, if we're in DST, and the last time in the timeline is "padding" (hour==0), then we don't need to
    bother asking for that date, as by definition we'll always receive an extra hour of data from the previous
    day's returned data.
    """
    if not tz.isDst(timeline[0]):
        logger.debug(
            f"No DST changes to request dates {timeline[0].date().strftime('%Y-%m-%d')} - {timeline[-1].date().strftime('%Y-%m-%d')}"
        )
        return timeline[0].date(), timeline[-1].date()

    # If they want data for the first hour of the day, we need to ask for the previous day to get that data.
    if timeline[0].hour == 0:
        requested_start_date = timeline[0].date() - timedelta(days=1)
    else:
        requested_start_date = timeline[0].date()

    if timeline[-1].date() != timeline[0].date() and timeline[-1].time() == time(0):
        # The timeline was "padded" with an extra time for midnight the following day.
        # Since we have that hour included, we don't need to ask for it.
        requested_end_date = timeline[-1].date() - timedelta(days=1)
    else:
        # The timeline was not padded, so always ask for the last date. We just won't use the last hour of data.
        requested_end_date = timeline[-1].date()

    logger.debug(
        f"Timeline: {timeline[0].date().strftime('%Y-%m-%d')} "
        f"- {timeline[-1].date().strftime('%Y-%m-%d')}, "
        "Requesting CDMO dates: "
        f"{requested_start_date.strftime('%Y-%m-%d')} - "
        f"{requested_end_date.strftime('%Y-%m-%d')}"
    )

    return requested_start_date, requested_end_date


def find_hilos(timeline, obs_dict) -> dict:
    """Given a key-ordered timeline and dense dict of tide readings {datetime: level}, return a dense dict of
    {dt: 'H' or 'L'} indicating which of the datetimes correspond to a high or low tide.

    In this function, an "arc" is a series of consecutive tide readings which may may contain a high or low
    tide. Values above the mid-tide level are a potential high tide arc, and below it, a low tide arc.
    We take the max/min value from each arc to look for the high/low tide.  Mid-tide is defined
    as defined as the average of the highest and lowest value seen in the data, with a minimum allowable
    value in case of lots of missing data. Since we have to account for missing, and possibly spurious
    values, we take a somewhat conservative approach -- false negatives are preferable to false positives.

    We are expecting a timeline with full days, at 96 per day, so whether we are dealing with a diurnal
    or semidiurnal station, there should be at least 1 high and 1 low per day.  Missing data values (None)
    are tolerated, but peaks and troughs are identified by consecutive values like [9.5, 10.1, 9.9] and
    [2.5, 2.1, 2.1, 2.3], and any None embedded in these will cause us to ignore the arc, since they could
    be disguising the actual peak or trough.
    """

    MIN_TIDAL_RANGE = (
        4  # In feet. If range is less than this, there's likely a lot of missing data.
    )
    (HIGH_ARC, LOW_ARC) = ("H", "L")
    hilomap = {}  # {dt: 'H' or 'L'}

    if len(obs_dict) == 0:
        return hilomap  # nothing to do

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

    # Walk through the timeline and identify arcs.  An arc is a half-cycle of the wave -- above or below the
    # midline, each of which may contain a high or low tide.
    arcs = []  # [{position: H/L, datadict: {dt: level}}]  datadict is dense and key-ordered

    cur_arc = None
    for dt in timeline:
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
            filter(lambda dt: min(datadict) <= dt <= max(datadict), timeline)
        )
        sparce_vals = [datadict.get(dt, None) for dt in arc_timeline]
        # The first and last values are not candidates for high or low tide, since there's no value on the other
        # side to prove it.
        if sparce_vals[0] == hilo_val or sparce_vals[-1] == hilo_val:
            logger.debug(
                f"hi/lo {hilo_val} found at beginning or end of arc beginning at {arc_timeline[0]}"
            )
            continue
        # We need to see a peak or trough with no None's breaking it up. E.g. [7,8,7] or [3,2,2,3] Not [7,8,None,7]
        ndx = sparce_vals.index(hilo_val)  # returns the 1st instance of the high/low.
        if sparce_vals[ndx - 1] is None:
            logger.debug(
                f"None found before hi/lo {hilo_val} in arc beginning at {arc_timeline[0]}"
            )
            continue
        # Finally check the right side. Any number of repeats are allowed, but must end with a different value.
        accepted = False
        for val in sparce_vals[ndx + 1 :]:
            if val is None:
                logger.debug(
                    f"None found after {hilo_val} in arc beginning at {arc_timeline[0]}"
                )
                break
            if val != hilo_val:
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


def handle_navd88_level(level_str: str, local_dt: datetime):
    """Convert tide string in navd88 meters to MLLW feet. Returns None if bad data."""
    if level_str is None or len(level_str.strip()) == 0:
        return None
    try:
        read_level = float(level_str)
        level = util.navd88_meters_to_mllw_feet(read_level)
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
