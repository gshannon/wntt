import copy
import functools
import logging
import pprint
from datetime import datetime, timedelta

import sentry_sdk

from . import tzutil as tz

logger = logging.getLogger(__name__)


def request_logger(func):
    """Decorator to handle error handling for calls to requests.get().  Since these are generally
    expected errors, no stack trace is printed."""

    logger = logging.getLogger(func.__module__)  # Use decorated func's logger, not ours

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"{type(e)} in {func.__module__}.{func.__name__}: {e}", stack_info=False
            )
            # Wind forecast is non-essential, so for this we just log and go on.
            if func.__module__.endswith("windforecast"):
                sentry_sdk.capture_exception(e)
                return {}
            raise

    return wrapper


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


def meters_to_feet(meters):
    return round(meters * 3.28084, 2)


def feet_to_meters(feet):
    return round(feet / 3.28084, 2)


def kilometers_to_miles(k: float) -> float:
    return round(k * 0.6213712, 1)


def meters_per_second_to_mph(mps: float) -> float:
    miles_per_sec = mps * 0.000621371
    return round(miles_per_sec * 3600, 1)


def mph_to_meters_per_second(mph: float) -> float:
    meters_per_sec = mph / 3600
    return round(meters_per_sec / 0.000621371, 1)


def celsius_to_fahrenheit(celsius: float) -> float:
    return round(celsius * 9 / 5 + 32, 1)


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    return round((fahrenheit - 32) * 5 / 9, 1)


def read_file(filepath):
    with open(filepath) as file:
        contents = file.read()
    return contents


def dump_xml(xml, filePath=None):
    decoded = bytes.fromhex(xml.hex()).decode("ASCII")
    if filePath is None:
        print(decoded)
    else:
        with open(filePath, "w") as file:
            file.write(decoded)


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
