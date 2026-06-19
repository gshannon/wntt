import copy
import logging
import pprint
from datetime import datetime, timedelta

from . import tzutil as tz

logger = logging.getLogger(__name__)


# This custom exception indicates a programming error.
class InternalError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def get_timeline_boundaries(timeline, asof=None, dbg=False) -> tuple[int, int]:
    """Return (timeline index of 1st past point, or -1, and index of first point >= present, or -1"""
    cutoff = asof or tz.now(timeline[0].tzinfo)
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
    m15 = timedelta(minutes=15)
    floor_mins = (dt.minute // 15) * 15
    floor = datetime(dt.year, dt.month, dt.day, dt.hour, floor_mins, tzinfo=dt.tzinfo)
    if dt.minute <= floor_mins + 7:
        return floor
    else:
        return floor + m15


def kilometers_to_miles(k: float) -> float:
    return round(k * 0.6213712, 1)


def meters_per_second_to_mph(in_value: float) -> float:
    """Convert meters/sec to miles/hour"""
    miles_per_sec = in_value * 0.000621371
    return round(miles_per_sec * 3600, 1)


def centigrade_to_fahrenheit(in_value: float) -> float:
    return round(in_value * 9 / 5 + 32, 1)


def read_file(filepath):
    with open(filepath) as file:
        contents = file.read()
    return contents


def dump_xml(xml, filename=None):
    decoded = bytes.fromhex(xml.hex()).decode("ASCII")
    if filename is None:
        print(decoded)
    else:
        f = open(filename, "w")
        f.write(decoded)
        f.close()


def pply(fig, data=False):
    pp = pprint.PrettyPrinter(indent=2)  # initialises a pretty printer
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
