from datetime import datetime, date, time, timedelta
from pytz import timezone
import logging


"""Provides some basic Timezone support. Isolating it here because timezone support in Python is confusing
and sometimes well known to be broken.  If all code uses these functions, we can improve it as needed in one spot. 
For example, say you have a US/Eastern datetime for noon on Spring forward day (3/10/2024). 
    dt = timezone('US/Eastern').localize(datetime(2024,3,10,12))
You can detect that it's in DST:
    dt.dst() == timedelta(seconds=3600).  
However, when you do:
    day_before = dt - timedelta(days=1)
this should clearly no longer be in DST.  But using timedelta does not update the dst(), which is still 
timedelta(seconds=3600). So instead you have to make sure you only call timedelta on UTC or naive datetimes.

FYI, some DST dates are:
3/12/2023 - 11/5/2023
3/10/2024 - 11/3/2024
3/9/2025 - 11/2/2025 
"""

logger = logging.getLogger(__name__)
eastern = timezone('US/Eastern')
central = timezone('US/Central')
mountain = timezone('US/Mountain')
pacific = timezone('US/Pacific')
utc = timezone('UTC')


def now(tzone) -> datetime:
    """Return current datetime in given time zone"""
    # This is the only way I know to do it if you don't want to
    # rely on knowing the timezone of the host.
    in_utc = utc.localize(datetime.utcnow())
    return in_utc.astimezone(tzone)


def naive_utc5_to_utc(dt: datetime) -> datetime:
    """Converts a CDMO-style "UTC-5" datetime to UTC.  Make a UTC out of it, then roll
    it forward 5 hours.  e.g. 2024-06-01 23:00 would become 2024-06-02 04:00 UTC
    """
    return utc.localize(dt) + timedelta(hours=5)
