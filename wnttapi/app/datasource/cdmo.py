import xml.etree.ElementTree as ElTree
from suds.client import Client
from datetime import datetime, date, time, timedelta
from app import util
from app import tzutil as tz
from rest_framework.exceptions import APIException
import logging

"""
Utility data and functions for graph building. 
"""

logger = logging.getLogger(__name__)
cdmo_wsdl = "https://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl"
wells_station = 'welinwq'
wells_met_station = 'wellfmet'
windspeed_param = 'Wspd'
windgust_param = 'MaxWspd'
winddir_param = 'Wdir'
tide_param = 'Level'
temp_param = 'Temp'
min_tide = -2.0  # any mllw/feet tide reading lower than this is considered bad data
max_tide = 20.0  # any mllw/feet tide reading higher than this is considered bad data
max_wind_speed = 120  # any wind speed reading higher than this is considered bad data


def get_recorded_tides(timeline: list) -> list:
    """
    For the given timeline, get a list of tide water levels from CDMO in MLLW feet, corresponding toe the timeline.
    """

    if timeline[0] > tz.now(timeline[0].tzinfo):
        # Nothing to fetch, it's all in the future
        return None

    raw_levels, data_count = get_cdmo(timeline, station=wells_station,
                                      param=tide_param,
                                      converter=handle_navd88_level, included_minutes=[0, 15, 30, 45])

    # HACK. In case there are no data points at all (all levels are None), we have chosen to display an empty graph.
    # However, plotly express blows up if all data points are None.  So we cheat.
    if data_count == 0:
        raw_levels[0] = 0.0

    logger.debug(f'Retrieved {len(raw_levels)} tide values from cdmo')
    if len(raw_levels) != len(timeline):
        raise APIException()

    return raw_levels


def get_recorded_wind_data(timeline: list) -> tuple[list, list, list, list]:
    """
    For the given list of timezone-aware datetimes, get a list of wind speeds and wind directions from CDMO.
    Returned data is corrected for daylight savings time as needed.
    """

    # If this is for the future, don't bother.
    if timeline[0].date() > tz.now(timeline[0].tzinfo).date():
        return None, None, None, None

    # The graph gets very dense, so we'll reduce the granularity as the day range increases
    days = (timeline[-1].date() - timeline[0].date()).days + 1
    if days > 5:
        minutes = [0]  # only show 1 point per hour
    elif days > 2:
        minutes = [0, 30]  # show 2 per hour
    else:
        minutes = [0, 15, 30, 45]  # show all 4

    speed_data, speed_count = get_cdmo(timeline, wells_met_station, windspeed_param, handle_windspeed, minutes)
    gust_data, cnt = get_cdmo(timeline, wells_met_station, windgust_param, handle_windspeed, minutes)
    dir_data, cnt = get_cdmo(timeline, wells_met_station, winddir_param, lambda d, dt: int(d), minutes, 0)

    # HACK. In the unlikely case there are no speed data points at all (all None), we have chosen to display
    # an empty graph. However, there's a quirk in plotly express where it crashes if all data points are None.
    # So we cheat and add a zero.
    if speed_count == 0:
        speed_data[0] = gust_data[0] = dir_data[0] = 0

    # Plotly can't handle a None in the wind direction data, so if there are any, we must set the speed
    # values to None also so plotly just skips the data point.
    for ii in range(len(dir_data)):
        if dir_data[ii] is None:
            logger.error(f'Found None wind dir for index {ii}')
            speed_data[ii] = gust_data[ii] = None

    # We want to show compass point names instead of degrees, so build a list for that too
    dir_strs = []
    for degrees in dir_data:
        dir_strs.append(util.degrees_to_dir(degrees) if degrees is not None else None)

    return speed_data, gust_data, dir_data, dir_strs

def get_recorded_temps(timeline: list) -> list:
    """
    For the given list of timezone-aware datetimes, get a list of water temp readings from CDMO.
    Returned data is corrected for daylight savings time as needed.
    """
    if timeline[0] > tz.now(timeline[0].tzinfo):
        # Nothing to fetch, it's all in the future
        return None

    raw_levels, _ = get_cdmo(timeline, station=wells_station,
                                      param=temp_param,
                                      converter=handle_float, included_minutes=[0, 15, 30, 45])
    return raw_levels

def dump_all_codes():
    """Utility function to dump all NERRS metadata to a file."""
    soap_client = Client(cdmo_wsdl, timeout=90, retxml=True)
    try:
        xml = soap_client.service.exportStationCodesXMLNew()
        util.dump_xml(xml, '/surgedata/StationCodes.xml')
    except Exception as e:
        logger.error(f"Error getting all codes from CDMO", exc_info=e)
        raise APIException()
    root = ElTree.fromstring(xml)  # ElementTree.Element
    return root

def get_cdmo(timeline: list, station: str, param: str, converter, included_minutes: list, noval=None) -> tuple[list, int]:
    """
    Get XML data from CDMO, parse it, convert timestsamps to requested timezone.
    Returns:
    * list of data which corresponds exactly to the given timeline.  Any missing data is None.
    * a count of data points which are not None

    Parameters
    ==========
    timeline : datetimes (tz aware) requested by the user, in ordered 15-minute intervals
    station : name of the station that is the data source
    param : name of the data parameter being requested
    converter : a function to convert a data point into the desired type, e.g. float or int, or unit conversion
    included_minutes : subset of [0,15,30,45] to indicate which data points to populate in each hour. Giving a subset
        allows you to display a sparser graph.
    noval : value to use for a missing or invalid point. e.g. 0.

    As of Feb 2024, these CDMO endpoints will return a maximum of 1000 data points. At 96 points per day (4 per hour),
    that's about 10.5 days. Therefore, no more than 10 days should be requested.  If you ask for more, CDMO truncates
    data points starting from the MOST RECENT data, not the latest.  So care should be taken not to ask for too much,
    else data at the beginning of the graph will be missing.
    """

    # If the start date is in DST, but not the day of the switchover, we'll need the preceding day also,
    # to get the last hour of that day, which is really the 1st hour of the start_date.
    start_date = timeline[0].date()
    end_date = timeline[-1].date()

    cdmo_start_date, cdmo_end_date = compute_cdmo_request_dates(start_date, end_date, timeline[0].tzinfo)
    soap_client = Client(cdmo_wsdl, timeout=90, retxml=True)

    try:
        xml = soap_client.service.exportAllParamsDateRangeXMLNew(station, cdmo_start_date, cdmo_end_date, param)
    except Exception as e:
        logger.error(f"Error getting {param} data {cdmo_start_date} to {cdmo_end_date} from CDMO", exc_info=e)
        raise APIException()

    root = ElTree.fromstring(xml)  # ElementTree.Element

    # Build a dict with key=datetime of the xml data, and val=the read value
    datadict = {}
    data_points = 0
    text_check(root.find(".//data"))
    for reading in root.findall(".//data"):  # use XPATH to dig out our data points
        date_str = reading.find("./DateTimeStamp").text
        try:
            dt_in_utc5 = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
        except ValueError:
            logger.error(f"Skipping bad datetime '{date_str}'")
            continue
        if dt_in_utc5.minute in included_minutes:
            # We need this naive UTC-5 in the local time. As always, first convert to UTC.
            in_utc = tz.naive_utc5_to_utc(dt_in_utc5)
            # Now convert to requested tzone, so DST is handled properly
            dt_in_local = in_utc.astimezone(timeline[0].tzinfo)
            data_str = reading.find(f"./{param}").text
            try:
                value = converter(data_str, dt_in_local)
            except (TypeError, ValueError):
                logger.error(f'Invalid {param} for {dt_in_utc5}: \'{data_str}\'')
                value = noval
            if value != noval:
                datadict[dt_in_local] = value

    # Now we have the data in a dict keyed by datetime in the same tz as the timeline, so we can assemble
    # the data list that corresponds to the timeline.
    data = []
    for dt in timeline:
        if dt in datadict:
            data.append(datadict[dt])
            data_points += 1
        else:
            data.append(noval)

    return data, data_points


def text_check(non_text_node):
    """If a node is not supposed to have text, return that text, else None
    This is how CDMO returns an error e.g. Invalid IP address.
    """
    try:
        message = non_text_node.text.strip()
        if len(message) > 0:
            logger.error(f"Got unexpected message from CDMO: {message}")
            raise APIException(message)
    except AttributeError:
        pass


def compute_cdmo_request_dates(requested_start_date: date, requested_end_date: date, tzone) -> tuple[date, date]:
    """All CDMO data unfortunately uses a made up timezone I'm calling UTC5, which is UTC - 5 hr year round.
    We may need to adjust the requested date range so the returned data matches the local time. Essentially,
    for every timezone except US/Eastern when it's not in DST (because that matches UTC5 precisely), we'll need to
    widen the range by a day, either by moving the start date back, or pushing the end date ahead, so we don't miss data.
    """
    naive_start_time = datetime.combine(requested_start_date, time(0))
    local_start_time = naive_start_time.replace(tzinfo=tzone)
    # Convert the start time we want into UTC.
    utc_required_start_time = local_start_time.astimezone(tz.utc)
    # Convert the start time we want into what CDMO would give us, in UTC.
    cdmo_start_time = tz.naive_utc5_to_utc(naive_start_time)

    # Now if the cdmo time is later than what we need, we'll miss data unless we move the start date back a day.
    # E.g. if we need 06/01/2024 00:00 in EDT, that's 06/01/2024 04:00 UTC, but the data we'll get back from
    # CDMO will actually start at 06/01/2024 00:00 UTC5, which is 06/01/2024 05:00 UTC.
    if cdmo_start_time > utc_required_start_time:
        return requested_start_date - timedelta(days=1), requested_end_date

    # So the start date is ok. Let's see if we have to move the end date ahead.
    naive_end_time = datetime.combine(requested_end_date, time(23, 45))
    local_end_time = naive_end_time.replace(tzinfo=tzone)
    # Convert the end time we want into UTC.
    utc_required_end_time = local_end_time.astimezone(tz.utc)
    # Convert the end time we want into what CDMO would give us, in UTC.
    cdmo_end_time = tz.naive_utc5_to_utc(naive_end_time)

    if cdmo_end_time < utc_required_end_time:
        # Since the cdmo end time is earlier than what we need, we'll miss data unless we move the end date ahead.
        # E.g. if we need up to 12/01/2023 23:45 in PST, that's 12/02/2023 07:45 UTC, but the data we'll get back from
        # CDMO will actually end at 12/01/2023 23:45 UTC5, which is 12/02/2023 04:45 UTC.
        return requested_start_date, requested_end_date + timedelta(days=1)

    return requested_start_date, requested_end_date


def handle_float(data_str: str, local_dt: datetime):
    """Convert string to float. Returns None if bad data."""
    if data_str is None or len(data_str.strip()) == 0:
        return None
    try:
        value = float(data_str)
    except ValueError:
        logger.error(f'Invalid float for {local_dt}: \'{data_str}\'')
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
            logger.error(f'level out of range for {local_dt}: {level} (raw: {read_level})')
            level = None
    except ValueError:
        logger.error(f'invalid level: [{level_str}]')
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
            logger.error(f'wind speed out of range for {local_dt}: {read_wspd} mps converted to {mph} mph')
            mph = None
    except ValueError:
        logger.error(f'invalid windspeed: [{wspd_str}]')
        mph = None
    return mph
