#! /usr/bin/env python3
# To run, this must be set in the env:
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]
# To run outside docker, cd to wnttapix.

import sys

# In the container, this is run from /wnttapi
sys.path.append(".")

# Django must be set up before importing models.
from django import setup

setup()

import argparse
import logging
import os
from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max

import app.datasource.cdmo as cdmo
import app.station as stn
import app.tzutil as tz
from app.models import Water, Wind, get_station
from app.timeline import Timeline

logger = logging.getLogger(__name__)


def main():

    nocontainer = os.environ.get("IN_CONTAINER", "-") != "1"

    parser = build_parser()
    args = parser.parse_args()
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
        repeat("T", station, db_station_code, timeline, args.debug, 3)
    if args.type is None or args.type == "W":
        repeat("W", station, db_station_code, timeline, args.debug, 3)


def repeat(
    type: str,
    station: stn.Station,
    db_station_code: str,
    timeline: Timeline,
    debug: bool,
    tries: int,
):
    for attempt in range(1, tries + 1):
        try:
            if attempt > 1:
                logger.warning(f"trying attempt #{attempt}")
            refresh(type, station, db_station_code, timeline, debug)
            break
        except Exception as exc:
            # Only log the error on the last attempt, since errors get sent to sentry.
            if attempt == tries:
                logger.error(f"Failed to refresh data after {tries} attempts")
            else:
                logger.error(str(exc))


def refresh(
    type: str,
    station: stn.Station,
    db_station_code: str,
    timeline: Timeline,
    debug: bool,
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
        cdmo_data = cdmo.get_water_data(station, timeline, useDb=False)
    else:
        cdmo_data = cdmo.get_wind_data(station, timeline, useDb=False)

    if cdmo_data is not None and len(cdmo_data) > 0:
        if debug:
            diff(cdmo_data, type, db_station_code)
        else:
            upsert(cdmo_data, type, db_station_code)
    else:
        logger.info(f"No new {name} data to refresh yet")


def diff(cdmo_data: dict, type: str, db_station_code: str):
    name = "water" if type == "T" else "wind"
    print(f"Diffing {len(cdmo_data)} {name} records")
    diff_cnt = 0
    for dt, value in cdmo_data.items():
        qdt = dt.astimezone(tz.utc).isoformat()
        try:
            if type == "T":
                record = Water.objects.get(
                    station__exact=db_station_code, time__exact=(qdt)
                )
                diff_cnt += diff_water_record(record, value)
            else:
                record = Wind.objects.get(
                    station__exact=db_station_code, time__exact=(qdt)
                )
                diff_cnt += diff_wind_record(record, value)
        except ObjectDoesNotExist:
            print(f"{dt} not in database")

    print(f"Found {diff_cnt} diffs out of {len(cdmo_data)}")


def diff_water_record(db_rec, new_rec):
    if db_rec.level != new_rec.get(cdmo.Param.Tide.label) or db_rec.temp != new_rec.get(
        cdmo.Param.Temperature.label
    ):
        print(
            f"{db_rec.time} old/new level: {db_rec.level}/{new_rec['level']}, temp: {db_rec.temp}/{new_rec['temp']}",
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


def upsert(cdmo_data: dict, type: str, db_station_code: str):
    name = "water" if type == "T" else "wind"
    for dt, value in cdmo_data.items():
        if type == "T":
            Water.objects.update_or_create(
                station=db_station_code,
                time=dt.astimezone(tz.utc).isoformat(),
                defaults={
                    "level": value.get(cdmo.Param.Tide.label, None),
                    "temp": value.get(cdmo.Param.Temperature.label, None),
                },
            )
        else:
            Wind.objects.update_or_create(
                station=db_station_code,
                time=dt.astimezone(tz.utc).isoformat(),
                defaults={
                    "speed": value[cdmo.Param.WindSpeed.label],
                    "gust": value[cdmo.Param.WindGust.label],
                    "dir_deg": value[cdmo.Param.WindDir.label],
                },
            )
    logger.info(f"Wrote {len(cdmo_data)} {name} records to db")


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
    # parser.add_argument(
    #     "-l",
    #     "--local",
    #     action="store_true",
    #     help="No container, useful for debugging",
    #     required=False,
    # )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Debug mode",
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
