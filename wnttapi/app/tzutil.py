import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

"""Provides some basic Timezone support. Isolating it here because timezone support in Python is confusing.

General rules:

Build naive:
naive = datetime(2024,3,15,23,45)
naive = datetime.now()

Build aware:
datetime.now(tzinfo=eastern)
datetime.now().replace(tzinfo=central)
datetime(2024,6,1,tzinfo=pacific)
naive_datetime.replace(tzinfo=mountain)

Do NOT: datetime(2024,6,1).astimezone(ZoneInfo('US/Eastern')).  
This will first assume the naive datetime is machine timezone, then convert it to eastern.

Convert between aware timezones:
datetime(2024,6,18,10,14,tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('US/Eastern'))

Is a datetime tz aware?
dt.tzinfo is not None

Is an aware datetime in DST?
dst() returns None if dt is naive
dst() returns datetime.timedelta(seconds=0) if aware and not in DST
dst() returns datetime.timedelta(seconds=3600) if aware and in DST


FYI, some DST dates are:
3/12/2023 - 11/5/2023
3/10/2024 - 11/3/2024
3/9/2025 - 11/2/2025 
"""

logger = logging.getLogger(__name__)
eastern = ZoneInfo("US/Eastern")  # UTC-5 (std), UTC-4 (DST)
central = ZoneInfo("US/Central")  # UTC-6 (std), UTC-5 (DST)
mountain = ZoneInfo("US/Mountain")  # UTC-7 (std), UTC-6 (DST)
pacific = ZoneInfo("US/Pacific")  # UTC-8 (std), UTC-7 (DST)
hawaii = ZoneInfo("US/Hawaii")  # UTC-10 (std), no DST
utc = ZoneInfo("UTC")


def now(tzone) -> datetime:
    """Return current datetime in given time zone"""
    return datetime.now(tzone)


def isDst(dt: datetime) -> bool:
    """Returns whether the given datetime is in DST."""
    dst = dt.dst()
    if dst is None:
        raise ValueError("isDst() requires an aware datetime")
    return dst > timedelta(hours=0)
