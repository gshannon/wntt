#! /usr/bin/env python3
# You must have this in the env.
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]
import argparse
import logging
import sys
import os
from datetime import datetime

# In the container, this is run from /wnttapi
sys.path.append(".")

# Django must be set up before importing models.
from django import setup

setup()

import app.tzutil as tz
from app.datasource import astrotide as astro
from app.hilo import Hilo
from app.models import AstroTide15, AstroTideHilo
from app.station import get_station_with_noaa_id
from app.timeline import Timeline

logger = logging.getLogger(__name__)


"""
Inputs:
--noaa_id <noaa_station_id> : e.g. "8419317" for Wells
--start : start date YYYY-mm-dd
--end: end date YYYY-mm-dd
--debug: if true, compares with database values only

"""

# TODO: Add debug mode, to compare


def main():
    nocontainer = os.environ.get("IN_CONTAINER", "-") != "1"
    parser = argparse.ArgumentParser(
        description="Pull predicted tides from NOAA tides&currents service and upserts them in the database"
    )
    parser.add_argument("-n", "--noaa-id", help="NOAA station id", required=True)
    parser.add_argument("-S", "--start", help="start date, YYY-YM-MDD", required=True)
    parser.add_argument("-E", "--end", help="end date, YYYY-MM-DD", required=True)
    parser.add_argument(
        "-t",
        "--type",
        choices=["15", "HL"],
        help="data type: 15=15-min, HL=Hi/low. Default=both",
    )

    args = parser.parse_args()

    swmp_station = get_station_with_noaa_id(args.noaa_id, nocontainer)

    # We are pulling a specific date range, not just getting latest data.
    start_dt = tz.datetime_first(
        datetime.strptime(args.start, "%Y-%m-%d").date(), swmp_station.time_zone
    )
    end_dt = tz.datetime_last(
        datetime.strptime(args.end, "%Y-%m-%d").date(), swmp_station.time_zone
    )
    print(f"Processing {start_dt} to {end_dt} ...", file=sys.stderr)
    timeline = Timeline(start_dt, end_dt)

    if args.type is None or args.type == "15":
        upsert("15", args.noaa_id, timeline)
    if args.type is None or args.type == "HL":
        upsert("HL", args.noaa_id, timeline)


def unity(navd88_level):
    return navd88_level


def upsert(type, noaa_id, timeline):

    if type == "15":
        data15 = astro.get_15m_astro_tides(noaa_id, timeline, unity, False)

        for dt, level in data15.items():
            utc_dt = dt.astimezone(tz.utc)
            AstroTide15.objects.update_or_create(
                noaa_id=noaa_id, time=utc_dt.isoformat(), nav_level=level
            )
        print(f"Upserted {len(data15)} records")
    elif type == "HL":
        dataHilo = astro.get_hilo_astro_tides(noaa_id, timeline, unity, False)

        for dt, pred_hilo in dataHilo.items():
            utc_dt = dt.astimezone(tz.utc)
            utc_real_dt = pred_hilo.real_dt.astimezone(tz.utc)
            AstroTideHilo.objects.update_or_create(
                noaa_id=noaa_id,
                time=utc_dt.isoformat(),
                real_time=utc_real_dt.isoformat(),
                hilo="H" if pred_hilo.hilo == Hilo.HIGH else "L",
                nav_level=pred_hilo.value,
            )
        print(f"Upserted {len(dataHilo)} records")
    else:
        raise Exception(f"bad type: {type}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
