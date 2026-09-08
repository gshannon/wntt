#! /usr/bin/env python3

# Generate commands to upsert CDMO data for a date range.

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

datatype = "-t T"
start = datetime(2024, 1, 1, 0, 0, tzinfo=ZoneInfo("US/Eastern"))
end = datetime(2026, 8, 1, 0, 0, tzinfo=ZoneInfo("US/Eastern"))

cmd = "refresh-cdmo-data"

dt = start
while dt < end:
    e = dt + timedelta(days=7) - timedelta(minutes=15)
    print(
        f"{cmd} -s welinwq {datatype} -S {str(dt.isoformat())[0:16]} -E {str(e.isoformat())[0:16]}"
    )
    dt = dt + timedelta(days=7)
