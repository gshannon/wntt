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
from app.datasource import astrotide as astro
from app.datasource import cdmo
from app.models import Surge, SurgeBias
from app.station import Station, get_all_stations
from app.timeline import GraphTimeline

logger = logging.getLogger(__name__)
# minumum number of surge deltas required to calculate bias, out of possible 120
_min_deltas_required = 100
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
    calc_bias = (
        calculate_bias(
            args.noaa_station_id,
            filepath,
            args.date,
            args.cycle,
        )
        if args.noaa_station_id in BiaslessStations
        else None
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
                        "calc_bias": calc_bias,
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
    return None


# Calculate anomaly/bias for this file, log it to the database and return it so it can be applied to surge values.  This is only needed for stations in the BiaslessStations list.
def calculate_bias(
    noaa_station_id: str,
    filepath: str,
    filedate: datetime.date,
    cycle: int,
) -> float:
    swmp_station = get_swmp_station(noaa_station_id)
    end_dt = datetime.now(tz=swmp_station.time_zone)
    start_dt = end_dt - timedelta(days=5)
    tline = GraphTimeline(start_dt, end_dt, swmp_station.time_zone)
    tide_preds = astro.get_15m_astro_tides(swmp_station, tline)
    logger.debug(f"got {len(tide_preds)} tide predictions for bias calculation")
    obs_tides = cdmo.get_recorded_tides(swmp_station, tline)
    logger.debug(f"got {len(obs_tides)} tide obs for bias calculation")

    deltas = []
    # read the trailing 5 days of surge predictions from the file
    with open(filepath) as surge_file:
        reader = csv.reader(surge_file, skipinitialspace=True)
        next(reader)  # skip header
        for row in reader:
            date_str, surge_str = row[0], row[3]
            if int(date_str) % 100 != 0:
                continue
            dt = datetime.strptime(date_str, "%Y%m%d%H%M").replace(tzinfo=tz.utc)
            local_dt = dt.astimezone(swmp_station.time_zone)
            if start_dt <= local_dt <= end_dt and surge_str != _no_value:
                if local_dt in obs_tides and local_dt in tide_preds:
                    delta = obs_tides[local_dt] - (
                        tide_preds[local_dt] + float(surge_str)
                    )
                    deltas.append(round(delta, 2))
            elif local_dt > end_dt:
                break

    if len(deltas) < _min_deltas_required:
        logger.error(
            f"Only {len(deltas)} surge values found for bias calculation. Bias will not be calculated."
        )
        return None

    bias = round(sum(deltas) / len(deltas), 2)
    logger.info(
        f"Calculated bias for {swmp_station.id} on {filedate} cycle {cycle}: {bias} using {len(deltas)} deltas"
    )
    # Save to database.
    SurgeBias.objects.update_or_create(
        noaa_id=noaa_station_id, filedate=filedate, cycle=cycle, defaults={"bias": bias}
    )
    return bias


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
