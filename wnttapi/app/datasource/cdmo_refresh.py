#! /usr/bin/env python3
# You must have this in the env.
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]

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
from app.models import Water, Wind
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
    repeat(refresh_water, station, 3)
    repeat(refresh_wind, station, 3)


def repeat(func: callable, station: stn.Station, tries: int):
    for attempt in range(1, tries + 1):
        try:
            if attempt > 1:
                logger.warning(f"trying attempt #{attempt}")
            func(station)
            break
        except Exception as exc:
            logger.error(str(exc))


def refresh_water(station):
    logger.info(f"Refreshing CDMO water data for station {station.id} ...")

    # Find the most recent time for water data.
    last_dt_str = Water.objects.aggregate(Max("time", default=None))["time__max"]
    # Refresh the missing data, up to 7 days.
    # calling fromisoformat, it sets tzinfo to a 'datetime.timezone' type, not ZoneInfo. This mismatch
    # breaks our code, so to keep things simple, just replace that here with a ZoneInfo.
    last_dt = datetime.fromisoformat(last_dt_str).replace(tzinfo=tz.utc)
    now = datetime.now(tz=tz.utc)
    max_dt = min(now, last_dt + timedelta(days=7))  # limit to 7 days
    timeline = Timeline(last_dt + timedelta(minutes=15), max_dt)
    water_data = cdmo.get_water_data(station, timeline, useDb=False)
    tide_dict = water_data.get(cdmo.Param.Tide, None)
    temp_dict = water_data.get(cdmo.Param.Temperature, None)
    # TODO: Rework this
    if tide_dict is not None and len(tide_dict) > 0:
        if temp_dict is None or len(temp_dict) != len(tide_dict):
            raise Exception("unexpected results")
        logger.info(f"Got {len(tide_dict)} water records from CDMO")
        for dt, value in tide_dict.items():
            # logger.debug(f"dt {dt}, value {value}")
            Water.objects.update_or_create(
                station="WE",
                time=dt.isoformat(),
                defaults={
                    "level": value,
                    "temp": temp_dict[dt],
                },
            )
        logger.info(
            f"Last saved data was at {last_dt}, wrote {len(tide_dict)} water records to db"
        )
    else:
        logger.info(
            f"Last saved data was at {last_dt}. No new water data to refresh yet"
        )


def refresh_wind(station):
    logger.info(f"Refreshing CDMO wind data for station {station.id} ...")

    # Find the most recent time for wind data.
    last_dt_str = Wind.objects.aggregate(Max("time", default=None))["time__max"]
    # Refresh the missing data, up to 7 days.
    # Note: we are working all in UTC here. time col in the db is ISO which is "+00:00" format. When
    # calling fromisoformat, it sets tzinfo to a 'datetime.timezone' type, not ZoneInfo. This mismatch
    # breaks our code, so to keep things simple, just replace that here with a ZoneInfo.
    last_dt = datetime.fromisoformat(last_dt_str).replace(tzinfo=tz.utc)
    now = datetime.now(tz=tz.utc)
    max_dt = min(now, last_dt + timedelta(days=7))  # limit to 7 days
    timeline = Timeline(last_dt + timedelta(minutes=15), max_dt)
    wind_dict = cdmo.get_wind_data(station, timeline, useDb=False)
    if wind_dict is not None and len(wind_dict) > 0:
        # TODO: Rework this
        for dt, value in wind_dict.items():
            logger.debug(f"dt {dt}, {value}")
            Wind.objects.update_or_create(
                station="WE",
                time=dt.isoformat(),
                defaults={
                    "speed": value["speed"],
                    "gust": value["gust"],
                    "dir_deg": value["dir"],
                    "dir_str": value["dir_str"],
                },
            )
        logger.info(
            f"Last saved data was at {last_dt}, wrote {len(wind_dict)} wind records to db"
        )
    else:
        logger.info(
            f"Last saved data was at {last_dt}. No new wind data to refresh yet"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
