#! /usr/bin/env python3
# To run, this must be set in the env:
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]

import argparse
import logging
import os
import sys
from datetime import date, datetime, time, timedelta

# In the container, this is run from /wnttapi
sys.path.append(".")

from django import setup
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

from tools.logging_config import force_console_logging

# Django must be set up before importing models or anything that imports them.
setup()
# Immediately reconfigure logging to console.  Now loggers in the following imports will log to console.
force_console_logging()

import app.station as stn
import app.tzutil as tz
from app.datasource import cdmo
from app.datasource.tides import Tide
from app.datasource.winds import Wind
from app.models import Water, get_station
from app.models import Wind as WindDb
from app.timeline import Timeline

# Can't use the normal __main__ logger because this is run as a script, not a module.
logger = logging.getLogger("tools.cdmo_refresh")

args = None
nocontainer = False


def main():

    global args, nocontainer
    nocontainer = os.environ.get("IN_CONTAINER", "-") != "1"

    parser = build_parser()
    args = parser.parse_args()
    if args.verbose and args.debug:
        print("Cannot have both verbose and debug")
        parser.print_help()
        return

    if nocontainer:
        station = stn.get_station(args.swmp_station_id, "../datamount/stations")
    else:
        station = stn.get_station(args.swmp_station_id)
    db_station_code = get_station(args.swmp_station_id)

    timeline = get_timeline(station)

    if args.type is None or args.type == "T":
        refresh("T", station, db_station_code, timeline)
    if args.type is None or args.type == "W":
        refresh("W", station, db_station_code, timeline)


def get_timeline(station) -> Timeline:
    if args.start is not None and args.end is not None:
        # We are pulling a specific time range.
        start_dt = datetime.strptime(args.start, "%Y-%m-%dT%H:%M").replace(
            tzinfo=station.time_zone
        )
        end_dt = datetime.strptime(args.end, "%Y-%m-%dT%H:%M").replace(
            tzinfo=station.time_zone
        )
        print(f"Processing {start_dt} to {end_dt} ...", file=sys.stderr)
        timeline = Timeline(start_dt, end_dt)
    elif args.year is not None and args.week is not None:
        start_date = date.fromisocalendar(int(args.year), int(args.week), 1)
        start_dt = datetime.combine(start_date, time(0), tzinfo=station.time_zone)
        end_dt = start_dt + timedelta(days=7) - timedelta(minutes=15)
        print(
            f"Processing week {args.week} of {args.year}: {start_dt} to {end_dt} ...",
            file=sys.stderr,
        )
        timeline = Timeline(start_dt, end_dt)
    else:
        timeline = None  # We'll just get the latest data

    return timeline


def getDumpPath(type):
    filePath = None
    if args.xmlsave:
        fname = datetime.now(tz=tz.utc).strftime("%Y%m%d-%H%M%S")
        if nocontainer:
            filePath = f"../datamount/cdmo/{fname}-{type}.xml"
        else:
            filePath = f"/data/cdmo/{fname}-{type}.xml"
        print(f"Will save {filePath}")
    return filePath


def refresh(
    type: str,
    station: stn.Station,
    db_station_code: str,
    timeline: Timeline,
):
    name = "water" if type == "T" else "wind"

    if timeline is None:
        # Get the latest data, up to 7 days.
        if type == "T":
            last_dt_str = Water.objects.aggregate(Max("time", default=None))[
                "time__max"
            ]
        else:
            last_dt_str = WindDb.objects.aggregate(Max("time", default=None))[
                "time__max"
            ]
        logger.debug(f"Last saved {name} data was for {last_dt_str}")
        timeline = build_latest_timeline(last_dt_str, station)

    logger.info(
        f"Refreshing CDMO {name} data for {station.id} "
        + f"{timeline.start_dt.strftime('%Y-%m-%d %H:%M')} - {timeline.end_dt.strftime('%Y-%m-%d %H:%M:00')}"
    )

    if type == "T":
        tides = cdmo.get_water_data(
            station, timeline, useDb=False, savePath=getDumpPath(type)
        )

        diffs = None
        if tides is not None and len(tides) > 0:
            if args.debug or args.verbose:
                diffs = diff_water(tides, db_station_code)
            if not args.debug and (diffs is None or diffs > 0):
                upsert_water(tides, db_station_code)
        else:
            logger.info(f"No matching {name} records found")

    else:
        winds = cdmo.get_wind_data(
            station, timeline, useDb=False, savePath=getDumpPath(type)
        )
        diffs = None

        if winds is not None and len(winds) > 0:
            if args.debug or args.verbose:
                diffs = diff_wind(winds, db_station_code)
            if not args.debug and (diffs is None or diffs > 0):
                upsert_wind(winds, db_station_code)
        else:
            logger.info(f"No matching {name} records found")


def diff_water(tides: dict, db_station_code: str) -> int:
    print(f"Diffing {len(tides)} water records")
    diff_cnt = 0
    for dt, cdmo_rec in tides.items():
        qdt = dt.astimezone(tz.utc).isoformat()
        try:
            db_rec = Water.objects.get(station=db_station_code, time=(qdt))
            diff_cnt += diff_water_record(db_rec, cdmo_rec)
        except ObjectDoesNotExist:
            diff_cnt += 1
            print(f"{dt} not in database")

    print(f"Found {diff_cnt} diffs out of {len(tides)} water cdmo records")
    return diff_cnt


def diff_wind(winds: dict, db_station_code: str) -> int:
    print(f"Diffing {len(winds)} wind records")
    diff_cnt = 0
    for dt, cdmo_rec in winds.items():
        qdt = dt.astimezone(tz.utc).isoformat()
        try:
            db_rec = WindDb.objects.get(station=db_station_code, time=(qdt))
            diff_cnt += diff_wind_record(db_rec, cdmo_rec)
        except ObjectDoesNotExist:
            diff_cnt += 1
            print(f"{dt} not in database")

    print(f"Found {diff_cnt} diffs out of {len(winds)} wind cdmo records")
    return diff_cnt


def diff_water_record(db_rec: WindDb, cdmo_rec: Wind) -> int:

    # We only diff Corrected water level, as temp is not important in this app
    if not cdmo_rec.nav_feet_equals(db_rec.clevel_nf):
        print(
            f"{db_rec.time} old/new clevel_nf: {db_rec.clevel_nf}/{cdmo_rec.corrected_nav_feet}",
        )
        return 1
    return 0


def diff_wind_record(db_rec: Water, cdmo_rec: Tide):
    if (
        db_rec.gust != cdmo_rec.gust_mph
        or db_rec.speed != cdmo_rec.speed_mph
        or db_rec.dir_deg != cdmo_rec.direction_deg
    ):
        print(
            (
                f"{db_rec.time} old/new speed: {db_rec.speed}/{cdmo_rec.speed_mph}, "
                + f"gust: {db_rec.gust}/{cdmo_rec.gust_mph} dir_deg: {db_rec.dir_deg}/{cdmo_rec.direction_deg}"
            ),
        )
        return 1
    return 0


def upsert_water(tides: dict, db_station_code: str):
    create_cnt = update_cnt = 0
    for dt, tide in tides.items():
        _, created = Water.objects.update_or_create(
            station=db_station_code,
            time=dt.astimezone(tz.utc).isoformat(),
            defaults={
                "temp_f": tide.temp_f,
                "clevel_nf": tide.corrected_nav_feet,
            },
        )
        if created:
            create_cnt += 1
        else:
            update_cnt += 1
    logger.info(f"Created {create_cnt}, updated {update_cnt} water records in db")


def upsert_wind(winds: dict, db_station_code: str):
    create_cnt = update_cnt = 0
    for dt, wind_rec in winds.items():
        _, created = WindDb.objects.update_or_create(
            station=db_station_code,
            time=dt.astimezone(tz.utc).isoformat(),
            defaults={
                "speed": wind_rec.speed_mph,
                "gust": wind_rec.gust_mph,
                "dir_deg": wind_rec.direction_deg,
            },
        )
        if created:
            create_cnt += 1
        else:
            update_cnt += 1
    logger.info(f"Created {create_cnt}, updated {update_cnt} wind records in db")


def build_latest_timeline(last_dt_str, station) -> Timeline:
    # Note: the db times are in UTC, stored in ISO format which is "+00:00". But when calling
    # datetime.fromisoformat, it sets tzinfo to a 'datetime.timezone' type, not ZoneInfo. This
    # means it only knows about tz offsets, not DST. So we convert that to a DST-aware ZoneInfo.
    last_dt_utc = datetime.fromisoformat(last_dt_str).replace(tzinfo=tz.utc)
    last_dt_local = last_dt_utc.astimezone(station.time_zone)
    now = datetime.now(tz=station.time_zone)
    max_dt_local = min(
        now, last_dt_local + timedelta(days=7)
    )  # don't ask for too much from cdmo
    timeline = Timeline(last_dt_local + timedelta(minutes=15), max_dt_local)
    return timeline


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--swmp_station_id", help="SWMP station id", required=True
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug mode, diff only no upserts",
        required=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose mode, diff and upserts",
        required=False,
    )
    parser.add_argument(
        "-t",
        "--type",
        required=False,
        choices=["T", "W"],
        help="data type: T=tide & temp, W=wind. Default=both",
    )
    parser.add_argument(
        "-S",
        "--start",
        required=False,
        help="start datetime in US/Eastern as YYYY-mm-ddTHH:MM",
    )
    parser.add_argument(
        "-E",
        "--end",
        required=False,
        help="end datetime in US/Eastern as YYYY-mm-ddTHH:MM",
    )
    parser.add_argument(
        "-y",
        "--year",
        required=False,
        help="Year to pull, use with --week",
    )
    parser.add_argument(
        "-w",
        "--week",
        required=False,
        help="Week to pull (1-52), use with --year",
    )
    parser.add_argument(
        "-x",
        "--xmlsave",
        required=False,
        action="store_true",
        help="Save all xml files",
    )
    return parser


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
