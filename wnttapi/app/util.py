from datetime import datetime, date, time, timedelta
import pprint
import copy
import logging
from django.conf import settings
from . import tzutil as tz
from . import config as cfg
from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=2)  # initialises a pretty printer


def build_timeline(start_date: date, end_date: date, time_zone, interval_minutes=15, extra=True) -> list:
    """Build a datetime list using the given interval in requested timezone for a given date range. If extra is
    requested, we add the 00:00 (midnight) of the following day past the range, so the graphs don't look truncated on
    the right side. If a daylight savings time boundary is included, you will get:
    - for spring forward, the 02:00 hour will be skipped
    - for fall back:
      01:00 daylight time
      01:15 daylight time
      01:30 daylight time
      01:45 daylight time
      01:00 standard time
      01:15 standard time
      01:30 standard time
      01:45 standard time
      02:00 standard time (etc)

      interval_minutes param must be a whole number factor of 1,440 (minutes in a day)
    """
    if (24 * 60) % interval_minutes != 0:
        raise APIException()
    if end_date < start_date:
        logger.error("end_date must be greater than start_date")
        raise APIException()
    local_start = datetime.combine(start_date, time(0)).replace(tzinfo=time_zone)
    # we'll go until the next day after the range, then consider removing the last entry later
    end_plus = end_date + timedelta(days=1)
    local_end = datetime.combine(end_plus, time(0)).replace(tzinfo=time_zone)
    utc_end = local_end.astimezone(tz.utc)
    # timedelta is broken when crossing DST boundaries in tz's which honor DST, so we'll do all the time
    # math in UTC and convert the answers back to local.
    data = []
    utc_cur = local_start.astimezone(tz.utc)
    while utc_cur <= utc_end:
        data.append(utc_cur.astimezone(time_zone))
        utc_cur += timedelta(minutes=interval_minutes)

    # Remove the extra time if they didn't want it
    if not extra:
        data.pop()

    return data


def get_timeline_info(timeline, asof=None) -> tuple[int, int]:
    """Return (timeline index of 1st past point, or -1, and index of first point >= present, or -1"""
    cutoff = asof if asof is not None else tz.now(timeline[0].tzinfo)
    if cutoff >= timeline[-1]:
        # All in the past. Note that even if the last time in the timeline matches the cutoff,
        # it makes no sense when graphing to call a single point at the end "future"
        return 0, -1
    if cutoff <= timeline[0]:
        # All in the future. Even if cutoff matches 1st time in timeline, it's better for the graph to ignore it.
        return -1, -1
    for ii, dt in list(enumerate(timeline)):
        if dt >= cutoff:
            return 0, ii


def round_to_quarter(dt: datetime) -> datetime:
    """round a datetime to nearest quarter-hour"""
    m15 = timedelta(minutes=15)
    floor_mins = (dt.minute // 15) * 15
    floor = datetime(dt.year, dt.month, dt.day, dt.hour, floor_mins, tzinfo=dt.tzinfo)
    if dt.minute <= floor_mins + 7:
        return floor
    else:
        return floor + m15


def navd88_feet_to_mllw_feet(in_value: float) -> float:
    return in_value + cfg.get_mllw_conversion()

def mllw_feet_to_navd88_feet(in_value: float) -> float:
    return in_value - cfg.get_mllw_conversion()


def navd88_meters_to_mllw_feet(in_value: float) -> float:
    feet = round(in_value * 3.28084, 2)
    return navd88_feet_to_mllw_feet(feet)

def mllw_feet_to_navd88_meters(in_value: float) -> float:
    feet = mllw_feet_to_navd88_feet(in_value)
    return round(feet / 3.28084, 2)


def meters_per_second_to_mph(in_value: float) -> float:
    """Convert meters/sec to miles/hour"""
    miles_per_sec = in_value * 0.000621371
    return round(miles_per_sec * 3600, 1)


def degrees_to_dir(degrees) -> str:
    if degrees <= 11:  # 23
        direction = 'N'
    elif degrees <= 33:  # 22
        direction = 'NNE'
    elif degrees <= 56:
        direction = 'NE'
    elif degrees <= 78:
        direction = 'ENE'
    elif degrees <= 101:
        direction = 'E'
    elif degrees <= 123:
        direction = 'ESE'
    elif degrees <= 146:
        direction = 'SE'
    elif degrees <= 168:
        direction = 'SSE'
    elif degrees <= 191:
        direction = 'S'
    elif degrees <= 213:
        direction = 'SSW'
    elif degrees <= 236:
        direction = 'SW'
    elif degrees <= 258:
        direction = 'WSW'
    elif degrees <= 281:
        direction = 'W'
    elif degrees <= 303:
        direction = 'WNW'
    elif degrees <= 326:
        direction = 'NW'
    elif degrees <= 348:
        direction = 'NNW'
    else:
        direction = 'N'
    return direction


def format_float(value, precision=5, suffix='') -> str:
    """Format a floating point value suitably for html displaying, with optional precision or suffex (e.g. ft)"""
    return f"{value:.{precision}f} {suffix}" if value else ''


def dump_xml(xml, filename):
    decoded = bytes.fromhex(xml.hex()).decode("ASCII")
    f = open(filename, 'w')
    f.write(decoded)
    f.close()


def pply(fig, data=False):
    if not data:
        # use copy to make sure we don't break the original figure dictionary
        po = copy.deepcopy(fig)
        for elem in po.data:
            elem['text'] = ['...']
            elem['x'] = ['...']
            elem['y'] = ['...']
        pp.pprint(po)
    else:
        pp.pprint(fig)
