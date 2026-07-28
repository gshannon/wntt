#! /usr/bin/env python3
# To run, this must be set in the env:
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

# In the container, this is run from /wnttapi
sys.path.append(".")

from django import setup
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

import app.station as stn
import app.tzutil as tz
from app.datasource.tides import Tide, Tides
from app.timeline import Timeline

# Django must be set up before importing models or anything that imports them.
setup()

import app.datasource.cdmo as cdmo
from app.models import Water, Wind, get_station

logger = logging.getLogger(__name__)


def main():

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

    if args.start is not None:
        # We are pulling a specific time range, not just getting latest data.
        start_dt = datetime.strptime(args.start, "%Y-%m-%dT%H:%M").replace(
            tzinfo=station.time_zone
        )
        end_dt = datetime.strptime(args.end, "%Y-%m-%dT%H:%M").replace(
            tzinfo=station.time_zone
        )
        print(f"Processing {start_dt} to {end_dt} ...", file=sys.stderr)
        timeline = Timeline(start_dt, end_dt)
    else:
        timeline = None

    if args.type is None or args.type == "T":
        refresh("T", station, db_station_code, timeline, args)
    if args.type is None or args.type == "W":
        refresh("W", station, db_station_code, timeline, args)


def refresh(
    type: str,
    station: stn.Station,
    db_station_code: str,
    timeline: Timeline,
    args,
):
    name = "water" if type == "T" else "wind"
    logger.info(
        f"Refreshing CDMO {name} data for station {station.id} / {db_station_code}..."
    )

    if timeline is None:
        # Get the latest data, up to 7 days.
        if type == "T":
            last_dt_str = Water.objects.aggregate(Max("time", default=None))[
                "time__max"
            ]
        else:
            last_dt_str = Wind.objects.aggregate(Max("time", default=None))["time__max"]
        logger.debug(f"Last saved {name} data was for {last_dt_str}")
        timeline = build_latest_timeline(last_dt_str, station)

    if type == "T":
        tides = cdmo.get_water_data(station, timeline, useDb=False)

        if tides is not None and tides.length > 0:
            if args.debug or args.verbose:
                diff_water(tides, db_station_code)
            if not args.debug:
                upsert_water(tides, db_station_code)
        else:
            logger.info(f"No new {name} data to refresh yet")

    else:
        cdmo_data = cdmo.get_wind_data(station, timeline, useDb=False)

        if cdmo_data is not None and len(cdmo_data) > 0:
            if args.debug or args.verbose:
                diff_wind(cdmo_data, db_station_code)
            if not args.debug:
                upsert_wind(cdmo_data, db_station_code)
        else:
            logger.info(f"No new {name} data to refresh yet")


def diff_water(tides: Tides, db_station_code: str):
    name = "water"
    print(f"Diffing {tides.length} {name} records")
    diff_cnt = 0
    for dt, tide in tides.data.items():
        qdt = dt.astimezone(tz.utc).isoformat()
        try:
            record = Water.objects.get(station=db_station_code, time=(qdt))
            diff_cnt += diff_water_record(record, tide)
        except ObjectDoesNotExist:
            print(f"{dt} not in database")

    print(f"Found {diff_cnt} diffs out of {tides.length}")


def diff_wind(cdmo_data: dict, db_station_code: str):
    name = "wind"
    print(f"Diffing {len(cdmo_data)} {name} records")
    diff_cnt = 0
    for dt, value in cdmo_data.items():
        qdt = dt.astimezone(tz.utc).isoformat()
        try:
            record = Wind.objects.get(station=db_station_code, time=(qdt))
            diff_cnt += diff_wind_record(record, value)
        except ObjectDoesNotExist:
            print(f"{dt} not in database")

    print(f"Found {diff_cnt} diffs out of {len(cdmo_data)}")


def diff_water_record(db_rec, new_rec: Tide) -> int:

    # We only diff Corrected water level, as temp is not important in this app
    if not new_rec.nav_feet_equals(db_rec.clevel_nf):
        print(
            f"{db_rec.time} old/new clevel_nf: {db_rec.clevel_nf}/{new_rec.corrected_nav_feet}",
        )
        return 1
    return 0


def diff_wind_record(db_rec, new_rec):
    if (
        db_rec.gust != new_rec.get(cdmo.Param.WindGust.label)
        or db_rec.speed != new_rec.get(cdmo.Param.WindSpeed.label)
        or db_rec.dir_deg != new_rec.get(cdmo.Param.WindDir.label)
    ):
        print(
            (
                f"{db_rec.time} old/new speed: {db_rec.speed}/{new_rec['speed']}, "
                + f"gust: {db_rec.gust}/{new_rec['gust']} dir_deg: {db_rec.dir_deg}/{new_rec['dir_deg']}"
            ),
        )
        return 1
    return 0


def upsert_water(tides: Tides, db_station_code: str):
    create_cnt = update_cnt = 0
    for dt, tide in tides.data.items():
        _, created = Water.objects.update_or_create(
            station=db_station_code,
            time=dt.astimezone(tz.utc).isoformat(),
            defaults={
                "temp": tide.temp_f,
                "level": tide.mllw_feet,
                "clevel_nf": tide.corrected_nav_feet,
            },
        )
        if created:
            create_cnt += 1
        else:
            update_cnt += 1
    logger.info(f"Created {create_cnt}, updated {update_cnt} water records in db")


def upsert_wind(cdmo_data: dict, db_station_code: str):
    for dt, value in cdmo_data.items():
        Wind.objects.update_or_create(
            station=db_station_code,
            time=dt.astimezone(tz.utc).isoformat(),
            defaults={
                "speed": value[cdmo.Param.WindSpeed.label],
                "gust": value[cdmo.Param.WindGust.label],
                "dir_deg": value[cdmo.Param.WindDir.label],
            },
        )
    logger.info(f"Wrote {len(cdmo_data)} wind records to db")


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
    return parser


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
