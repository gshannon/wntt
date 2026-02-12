#! /usr/bin/env python3
import argparse
import csv
import sys
from datetime import datetime, time, timedelta

# In the container, this is run from /wnttapi
sys.path.append(".")

import app.tzutil as tz
from django import setup

# Django must be set up before importing models.
setup()
from app.models import Surge

"""
Utility to log a batch of 6 storm surge predictions to a database.  It is intended to be run from 
outside the container by the surge file download job, which does not have access to sqlite3, using
docker compose.

Files are released daily as follows, in a 24-hour cycle which does not coincide with a single day.
- ~00:15 UTC: cycle 18 of prior day. Use predictions for 01:00, 02:00, 03:00, 04:00, 05:00, 06:00
- ~06:15 UTC: cycle 00. Use predictions for 07:00, 08:00, 09:00, 10:00, 11:00, 12:00
- ~12:15 UTC: cycle 06. Use predictions for 13:00, 14:00, 15:00, 16:00, 17:00, 18:00
- ~18:15 UTC: cycle 12. Use predictions for 19:00, 20:00, 21:00, 22:00, 23:00, 00:00

Inputs:
--station_id <station_id> : e.g. "welinwq" for wells
--date <date> : date of file publication, YYYYmmdd
--cycle <cycle> : 00, 06, 12 or 18 
"""

# You must have this in the env.
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]

NO_VALUE = "9999.000"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--station_id", help="NOAA station id", required=True)
    parser.add_argument("-d", "--date", help="YYYYMMDD", required=True)
    parser.add_argument("-c", "--cycle", help="cycle: 0, 6, 12 or 18", required=True)

    args = parser.parse_args()

    # Calculate range we're interested in. The cycle param really means first hour of the future,
    # at the time the surge file was published.
    cycle_time = datetime.combine(
        datetime.strptime(args.date, "%Y%m%d"), time(int(args.cycle))
    ).replace(tzinfo=tz.utc)
    # We start with cycle + 7 hours, and get 6 hourly values.
    # E.g. if it's 12:45 and we download cycle 06, this is our last chance to see 1300 - 1800.
    start_time = cycle_time + timedelta(hours=7)
    end_time = start_time + timedelta(hours=5)

    filepath = f"/data/surge/data/{args.station_id}.csv"

    with open(filepath) as surge_file:
        reader = csv.reader(surge_file, skipinitialspace=True)
        next(reader)  # skip header row
        for row in reader:
            #         TIME,    TIDE,      OB,   SURGE,    BIAS,      TWL
            # 202502181200,   2.275,9999.000,  -1.600,9999.000,   0.675
            date_str, tide_str, obs_str, surge_str, bias_str, total_str = row
            # Only the times on the hour have actual surge data.
            if int(date_str) % 100 != 0:
                continue
            dt = datetime.strptime(row[0], "%Y%m%d%H%M").replace(tzinfo=tz.utc)
            if start_time <= dt <= end_time:
                # If there's a value in OBServed column, something is seriously wrong.
                if obs_str != NO_VALUE:
                    print(
                        f"WARNING: {args.station_id}.csv at {date_str} has OBS value {obs_str}"
                    )
                Surge.objects.update_or_create(
                    noaa_id=args.station_id,
                    tide_time=dt,
                    defaults={
                        "tide": float(tide_str),
                        "surge": float(surge_str),
                        "bias": float(bias_str) if bias_str != NO_VALUE else None,
                        "total": float(total_str),
                    },
                )
            if dt >= end_time:
                break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
