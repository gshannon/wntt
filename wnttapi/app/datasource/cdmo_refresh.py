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
from datetime import datetime, timedelta

import app.datasource.cdmo as cdmo
import app.station as stn
import app.tzutil as tz
from app.models import Water, Wind, get_station
from app.timeline import Timeline
from django.db.models import Max

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--swmp_station_id", help="SWMP station id", required=True
    )
    parser.add_argument(
        "-n",
        "--nocontainer",
        action="store_true",
        help="No container",
        required=False,
    )

    args = parser.parse_args()
    if args.nocontainer:
        station = stn.get_station(args.swmp_station_id, "../datamount/stations")
    else:
        station = stn.get_station(args.swmp_station_id)
    station_code = get_station(args.swmp_station_id)
    repeat(refresh_water, station, station_code, 3)
    repeat(refresh_wind, station, station_code, 3)


def repeat(func: callable, station: stn.Station, station_code: str, tries: int):
    for attempt in range(1, tries + 1):
        try:
            if attempt > 1:
                logger.warning(f"trying attempt #{attempt}")
            func(station, station_code)
            break
        except Exception as exc:
            # Only log the error on the last attempt, since errors get sent to sentry.
            if attempt == tries:
                logger.error(f"Failed to refresh data after {tries} attempts")
            else:
                logger.warning(str(exc))


def refresh_water(station, station_code):
    logger.info(
        f"Refreshing CDMO water data for station {station.id} / {station_code}..."
    )

    # Find the most recent time for water data.
    last_dt_str = Water.objects.aggregate(Max("time", default=None))["time__max"]
    logger.info(f"Last saved water data was for {last_dt_str}")
    # Refresh the missing data, up to 7 days.
    timeline = build_timeline(last_dt_str, station)
    water_data = cdmo.get_water_data(station, timeline, useDb=False)
    # TODO
    # Clean the tide data of bogus zeros
    # if Param.Tide in params:
    #     data[Param.Tide] = clean_tide_data(data[Param.Tide], station)

    if water_data is not None and len(water_data) > 0:
        for dt, value in water_data.items():
            Water.objects.update_or_create(
                station=station_code,
                time=dt.astimezone(tz.utc).isoformat(),
                defaults={
                    "level": value.get(cdmo.Param.Tide.label, None),
                    "temp": value.get(cdmo.Param.Temperature.label, None),
                },
            )
        logger.info(f"Wrote {len(water_data)} water records to db")
    else:
        logger.info("No new water data to refresh yet")


def refresh_wind(station, station_code):
    logger.info(
        f"Refreshing CDMO wind data for station {station.id} / {station_code} ..."
    )

    # Find the most recent time for wind data.
    last_dt_str = Wind.objects.aggregate(Max("time", default=None))["time__max"]
    logger.info(f"Last saved wind data was for {last_dt_str}")
    # Refresh the missing data, up to 7 days.
    timeline = build_timeline(last_dt_str, station)
    wind_dict = cdmo.get_wind_data(station, timeline, useDb=False)

    if wind_dict is not None and len(wind_dict) > 0:
        for dt, value in wind_dict.items():
            Wind.objects.update_or_create(
                station=station_code,
                time=dt.astimezone(tz.utc).isoformat(),
                defaults={
                    "speed": value[cdmo.Param.WindSpeed.label],
                    "gust": value[cdmo.Param.WindGust.label],
                    "dir_deg": value[cdmo.Param.WindDir.label],
                    "dir_str": value[cdmo.WIND_DIRSTR_LABEL],
                },
            )
        logger.info(f"Wrote {len(wind_dict)} wind records to db")
    else:
        logger.info("No new wind data to refresh yet")


def build_timeline(last_dt_str, station) -> Timeline:
    # Note: we are working all in UTC here. time col in the db is ISO which is "+00:00" format. When
    # calling fromisoformat, it sets tzinfo to a 'datetime.timezone' type, not ZoneInfo. This means it
    # only knows about tz offsets, not DST. Here we convert to a DST-aware ZoneInfo.
    last_dt_utc = datetime.fromisoformat(last_dt_str).replace(tzinfo=tz.utc)
    last_dt_local = last_dt_utc.astimezone(station.time_zone)
    now = datetime.now(tz=station.time_zone)
    max_dt_local = min(now, last_dt_local + timedelta(days=7))  # limit to 7 days
    timeline = Timeline(last_dt_local + timedelta(minutes=15), max_dt_local)
    return timeline


if __name__ == "__main__":
    logger.info("Starting")
    try:
        main()
    except Exception as e:
        print(str(e))
    logger.info("Done")
