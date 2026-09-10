import functools
import logging
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import ParamSpec, TypeVar

import sentry_sdk

P = ParamSpec("P")
R = TypeVar("R")
logger = logging.getLogger(__name__)


def request_logger(func: Callable[P, R]) -> Callable[P, R]:
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"{type(e)} in {func.__module__}.{func.__name__}: {e}", stack_info=False
            )
            if func.__module__.endswith("windforecast"):
                sentry_sdk.capture_exception(e)
                return None  # type: ignore[return-value]  # deliberate: swallow non-essential wind-forecast failure
            raise

    return wrapper


# This custom exception indicates a programming error.
class InternalError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


def get_supported_years() -> list[int]:
    """
    Get the years the API supports, in order. By default this means the last 2 years, the current year,
    plus the next 2 years.
    """
    year = date.today().year  # noqa
    return [y for y in range(year - 2, year + 3)]


def round_to_quarter(dt: datetime) -> datetime:
    """round a datetime to nearest quarter-hour"""
    m15 = timedelta(minutes=15)
    floor_mins = (dt.minute // 15) * 15
    floor = datetime(dt.year, dt.month, dt.day, dt.hour, floor_mins, tzinfo=dt.tzinfo)
    if dt.minute <= floor_mins + 7:
        return floor
    else:
        return floor + m15


def meters_to_feet(meters: float) -> float:
    return round(meters * 3.28084, 2)


def feet_to_meters(feet: float) -> float:
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


def read_file(filepath: str) -> str:
    with open(filepath) as file:
        contents = file.read()
    return contents


def dump_xml(xml: bytes, filePath: str | None = None) -> None:
    decoded = bytes.fromhex(xml.hex()).decode("ASCII")
    if filePath is None:
        print(decoded)
    else:
        with open(filePath, "w") as file:
            file.write(decoded)
