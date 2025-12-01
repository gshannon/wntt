import copy
import logging
import pprint
from datetime import datetime, timedelta

from . import tzutil as tz

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=2)  # initialises a pretty printer


def get_timeline_boundaries(timeline, asof=None, dbg=False) -> tuple[int, int]:
    """Return (timeline index of 1st past point, or -1, and index of first point >= present, or -1"""
    cutoff = asof if asof is not None else tz.now(timeline[0].tzinfo)
    if dbg:
        print(f"timeline: {timeline}")
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
    if dt.minute % 15 == 0:
        return dt
    m15 = timedelta(minutes=15)
    floor_mins = (dt.minute // 15) * 15
    floor = datetime(dt.year, dt.month, dt.day, dt.hour, floor_mins, tzinfo=dt.tzinfo)
    if dt.minute <= floor_mins + 7:
        return floor
    else:
        return floor + m15


def round_up_to_quarter(dt: datetime) -> datetime:
    """Return the next higher 00/15/30/45 time relative to a datetime.
    01:14 becomes 01:15. 01:15 becomes 01:30."""
    new_minute = (dt.minute // 15 * 15) + 15
    return dt + timedelta(minutes=new_minute - dt.minute)


def meters_per_second_to_mph(in_value: float) -> float:
    """Convert meters/sec to miles/hour"""
    miles_per_sec = in_value * 0.000621371
    return round(miles_per_sec * 3600, 1)


def centigrade_to_fahrenheit(in_value: float) -> float:
    return round(in_value * 9 / 5 + 32, 1)


def degrees_to_dir(degrees) -> str:
    if degrees <= 11:  # 23
        direction = "N"
    elif degrees <= 33:  # 22
        direction = "NNE"
    elif degrees <= 56:
        direction = "NE"
    elif degrees <= 78:
        direction = "ENE"
    elif degrees <= 101:
        direction = "E"
    elif degrees <= 123:
        direction = "ESE"
    elif degrees <= 146:
        direction = "SE"
    elif degrees <= 168:
        direction = "SSE"
    elif degrees <= 191:
        direction = "S"
    elif degrees <= 213:
        direction = "SSW"
    elif degrees <= 236:
        direction = "SW"
    elif degrees <= 258:
        direction = "WSW"
    elif degrees <= 281:
        direction = "W"
    elif degrees <= 303:
        direction = "WNW"
    elif degrees <= 326:
        direction = "NW"
    elif degrees <= 348:
        direction = "NNW"
    else:
        direction = "N"
    return direction


def read_file(filepath):
    with open(filepath) as file:
        contents = file.read()
    return contents


def dump_xml(xml, filename):
    decoded = bytes.fromhex(xml.hex()).decode("ASCII")
    f = open(filename, "w")
    f.write(decoded)
    f.close()


def pply(fig, data=False):
    if not data:
        # use copy to make sure we don't break the original figure dictionary
        po = copy.deepcopy(fig)
        for elem in po.data:
            elem["text"] = ["..."]
            elem["x"] = ["..."]
            elem["y"] = ["..."]
        pp.pprint(po)
    else:
        pp.pprint(fig)
