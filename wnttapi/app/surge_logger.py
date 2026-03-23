#! /usr/bin/env python3
# You must have this in the env.
# DJANGO_SETTINGS_MODULE = project.settings.[dev|prod]
import argparse
import csv
import logging
import sys
from datetime import datetime, time, timedelta

# In the container, this is run from /wnttapi
sys.path.append(".")

# Django must be set up before importing models.
from django import setup

setup()

import app.tzutil as tz
import app.util as util
from app.datasource import astrotide as astro
from app.datasource import cdmo
from app.models import Surge, SurgeBias
from app.station import Station, get_all_stations
from app.timeline import Timeline

logger = logging.getLogger(__name__)
_no_value = "9999.000"

BiaslessStations = ["8419317"]  # Wells surge data has no bias (anomaly)


"""
Utility to persist in the database certain data about a batch of 6 storm surge predictions to a database.  It is intended to be run from 
outside the container by the surge file download job.

Files are released daily as follows, in a 24-hour cycle which does not coincide with a single day.
- ~00:15 UTC: cycle 18 of prior day. Use predictions for 01:00, 02:00, 03:00, 04:00, 05:00, 06:00
- ~06:15 UTC: cycle 00. Use predictions for 07:00, 08:00, 09:00, 10:00, 11:00, 12:00
- ~12:15 UTC: cycle 06. Use predictions for 13:00, 14:00, 15:00, 16:00, 17:00, 18:00
- ~18:15 UTC: cycle 12. Use predictions for 19:00, 20:00, 21:00, 22:00, 23:00, 00:00

Translating to Eastern Standard Time:
- ~01:15 EST: cycle 00. Use predictions for 02:00, 03:00, 04:00, 05:00, 06:00, 07:00
- ~07:15 EST: cycle 06. Use predictions for 08:00, 09:00, 10:00, 11:00, 12:00, 13:00
- ~13:15 EST: cycle 12. Use predictions for 14:00, 15:00, 16:00, 17:00, 18:00, 19:00
- ~19:15 EST: cycle 18. Use predictions for 20:00, 21:00, 22:00, 23:00, 00:00, 01:00

Translating to Eastern Daylight Time:
- ~02:15 EDT: cycle 00. Use predictions for 03:00, 04:00, 05:00, 06:00, 07:00, 08;00
- ~08:15 EDT: cycle 06. Use predictions for 09:00, 10:00, 11:00, 12:00, 13:00, 14:00
- ~14:15 EDT: cycle 12. Use predictions for 15:00, 16:00, 17:00, 18:00, 19:00, 20:00
- ~20:15 EDT: cycle 18. Use predictions for 21:00, 22:00, 23:00, 00:00, 01:00, 02:00

Inputs:
--noaa_station_id <noaa_station_id> : e.g. "8419317" for Wells
--date <date> : date of file publication, YYYYmmdd
--cycle <cycle> : 00, 06, 12 or 18 

Logic:
If reserve has no bias:
    - Load dict of CDMO tide observations for last 5 days, keyed by datetime.
    - Load dict of COOPS tide predictions for last 5 days, keyed by datetime.
    - Load dict of surge predictions from for last 5 days from the surge file, keyed by datetime.
    - Calculate bias based on these 3 dicts, log to bias table in database.
- Extract the "best" surge values for the target 6 hours (keep original bias values), log to surge table.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n", "--noaa_station_id", help="NOAA station id", required=True
    )
    parser.add_argument("-d", "--date", help="file date, YYYYMMDD", required=True)
    parser.add_argument("-c", "--cycle", help="cycle: 00, 06, 12 or 18", required=True)

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

    # Note that /data should be a mount point to the host file system
    filename = f"{args.noaa_station_id}-{args.date}-{args.cycle}.csv"
    filepath = f"/data/surge/data/{filename}"

    # Calculate a bias for stations that don't have one in the surge file.

    (calc_bias1, calc_bias2) = (None, None)
    if args.noaa_station_id in BiaslessStations:
        swmp_station = get_swmp_station(args.noaa_station_id)

        end_dt = util.round_to_quarter(datetime.now(tz=swmp_station.time_zone))
        start_dt = end_dt - timedelta(
            days=6
        )  # extra day to allow for missing observations
        timeline = Timeline(start_dt, end_dt)

        # 5-day bias
        calc_bias1 = calculate_bias(swmp_station, timeline, filepath, 120)

        # 6-hour bias
        start_dt = end_dt - timedelta(
            hours=12
        )  # extra hours to allow for missing observations
        timeline = Timeline(start_dt, end_dt)
        calc_bias2 = calculate_bias(swmp_station, timeline, filepath, 6)

        logger.info(
            f"Calculated bias for {swmp_station.id} on {args.date} cycle {args.cycle}: bias1={calc_bias1} bias2={calc_bias2}"
        )

        # Save to database.
        SurgeBias.objects.update_or_create(
            noaa_id=args.noaa_station_id,
            filedate=args.date,
            cycle=args.cycle,
            defaults={"bias": calc_bias1, "bias2": calc_bias2},
        )

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
            dt = datetime.strptime(date_str, "%Y%m%d%H%M").replace(tzinfo=tz.utc)
            if start_time <= dt <= end_time:
                # If there's a value in OBServed column, something is seriously wrong.
                if obs_str != _no_value:
                    print(f"WARNING: {filename} at {date_str} has OBS value {obs_str}")
                Surge.objects.update_or_create(
                    noaa_id=args.noaa_station_id,
                    tide_time=dt,
                    defaults={
                        "cycle": int(args.cycle),
                        "tide": float(tide_str),
                        "surge": float(surge_str),
                        "bias": float(bias_str) if bias_str != _no_value else None,
                        "calc_bias": calc_bias1,
                        "calc_bias2": calc_bias2,
                        "total": float(total_str),
                    },
                )
            if dt >= end_time:
                break


def get_swmp_station(noaa_station_id: str) -> Station:
    for id, data in get_all_stations().items():
        if data["noaaStationId"] == noaa_station_id:
            return Station.from_dict(id, data)

    raise Exception(f"Station with NOAA id {noaa_station_id} not found!")


# Calculate anomaly/bias for this file, log it to the database and return it so it can be applied to surge values.  This is only needed for stations in the BiaslessStations list.
def calculate_bias(
    swmp_station: Station, timeline: Timeline, filepath: str, minimum_deltas: int
) -> float:
    """We want to look at a certain number of recent tide observations and calculate an average
    delta between the observation and the predicted tide plus the published surge value.  We'll walk
    through the file top to bottom (in chronological order) and pull all the records that match the given
    timeline and for which there is sufficient data for calculating delta, then pull the last N of
    those deltas to get the average. So the given timeline should be large enough to allow for missing
    observations.
    """
    tide_preds = astro.get_15m_astro_tides(swmp_station, timeline)
    logger.debug(f"got {len(tide_preds)} tide predictions for bias calculation")
    obs_tides = cdmo.get_recorded_tides(swmp_station, timeline)
    logger.debug(f"got {len(obs_tides)} tide obs for bias calculation")

    deltas = []
    # Read the past surge predictions from the file for the given timeline.
    with open(filepath) as surge_file:
        reader = csv.reader(surge_file, skipinitialspace=True)
        next(reader)  # skip header
        for row in reader:
            date_str, surge_str = row[0], row[3]
            if int(date_str) % 100 != 0:
                continue
            dt = datetime.strptime(date_str, "%Y%m%d%H%M").replace(tzinfo=tz.utc)
            local_dt = dt.astimezone(swmp_station.time_zone)
            if (
                timeline.start_dt <= local_dt <= timeline.end_dt
                and surge_str != _no_value
            ):
                if local_dt in obs_tides and local_dt in tide_preds:
                    delta = obs_tides[local_dt] - (
                        tide_preds[local_dt] + float(surge_str)
                    )
                    deltas.append(round(delta, 2))
            elif local_dt > timeline.end_dt:
                break

    if len(deltas) < minimum_deltas:
        logger.error(
            f"Expected at least {minimum_deltas} deltas, found only {len(deltas)} for bias calculation. Bias will not be calculated."
        )
        return None

    # Now pull out the latest values that match the required minimum count.
    my_deltas = deltas[-minimum_deltas:]
    logger.info(
        f"Using {len(my_deltas)} deltas out of the {len(deltas)} extracted from file"
    )

    bias = round(sum(my_deltas) / len(my_deltas), 2)
    return bias


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
