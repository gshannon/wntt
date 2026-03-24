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

    # Calculate time window we're interested in. This is the next 6 hours after the file publication, which we
    # calculate based on the cycle number.
    cycle_time_utc = datetime.combine(
        datetime.strptime(args.date, "%Y%m%d"), time(int(args.cycle))
    ).replace(tzinfo=tz.utc)
    # Define a 6-hour block representing the "near future", i.e. the 6 hours which will no longer
    # be in the future in subsequent cycles.  This is the last -- and hopefully the most
    # accurate -- prediction we will make for each of these 6 hours.
    # The beginning of the block is "cycle + 7" hours.  E.g. if we download cycle 06 (usually done
    # at 12:45UTC), this is our last chance to see (6+7) 1300 - 1800 UTC.
    start_window_utc = cycle_time_utc + timedelta(hours=7)
    end_window_utc = start_window_utc + timedelta(hours=5)

    # Note that /data should be a mount point to the host file system
    filename = f"{args.noaa_station_id}-{args.date}-{args.cycle}.csv"
    filepath = f"/data/surge/data/{filename}"

    file_dict = load_file(filepath)

    # Calculate a bias for stations that don't have one in the surge file.

    (calc_bias1, calc_bias2, calc_bias3) = (None, None, None)
    if args.noaa_station_id in BiaslessStations:
        swmp_station = get_swmp_station(args.noaa_station_id)

        end_dt_stz = util.round_to_quarter(datetime.now(tz=swmp_station.time_zone))
        start_dt_stz = end_dt_stz - timedelta(
            days=6
        )  # extra day to allow for missing observations
        timeline = Timeline(start_dt_stz, end_dt_stz)

        # 5-day bias
        obs_tides = cdmo.get_recorded_tides(swmp_station, timeline)
        logger.debug(f"got {len(obs_tides)} tide obs for bias calculation")
        calc_bias1 = calculate_bias(swmp_station, timeline, file_dict, obs_tides, 120)

        # Since we now have 5 days of observations loaded, save them to the database as needed.
        save_observations(swmp_station, obs_tides)

        # 6-hour bias
        start_dt_stz = end_dt_stz - timedelta(
            hours=12
        )  # extra hours to allow for missing observations
        timeline = Timeline(start_dt_stz, end_dt_stz)
        calc_bias2 = calculate_bias(swmp_station, timeline, file_dict, obs_tides, 6)

        # 24-hour bias
        start_dt_stz = end_dt_stz - timedelta(
            hours=36
        )  # extra hours to allow for missing observations
        timeline = Timeline(start_dt_stz, end_dt_stz)
        calc_bias3 = calculate_bias(swmp_station, timeline, file_dict, obs_tides, 24)

        logger.info(
            f"Calculated bias for {swmp_station.id} on {args.date} cycle {args.cycle}: bias1={calc_bias1} bias2={calc_bias2} bias3={calc_bias3}"
        )

        # Save to database, for potential use by the app, to add bias to the surge from the file.
        SurgeBias.objects.update_or_create(
            noaa_id=args.noaa_station_id,
            filedate=args.date,
            cycle=args.cycle,
            defaults={"bias": calc_bias1, "bias2": calc_bias2, "bias3": calc_bias3},
        )

        # Now save the 6 records in the target window.
        for dt_utc, rec in file_dict.items():
            if start_window_utc <= dt_utc <= end_window_utc:
                # Look up the 24- and 48-hour surge predictions
                future_dt_24 = dt_utc + timedelta(days=1)
                future_dt_48 = dt_utc + timedelta(days=2)
                Surge.objects.update_or_create(
                    noaa_id=args.noaa_station_id,
                    tide_time=dt_utc,
                    defaults={
                        "cycle": int(args.cycle),
                        "tide": rec["tide"],
                        "surge": rec["surge"],
                        "surge_1day": file_dict[future_dt_24]["surge"],
                        "surge_2day": file_dict[future_dt_48]["surge"],
                        "bias": rec["bias"],
                        "calc_bias": calc_bias1,
                        "calc_bias2": calc_bias2,
                        "calc_bias3": calc_bias3,
                    },
                )
            if dt_utc >= end_window_utc:
                break


def get_swmp_station(noaa_station_id: str) -> Station:
    for id, data in get_all_stations().items():
        if data["noaaStationId"] == noaa_station_id:
            return Station.from_dict(id, data)

    raise Exception(f"Station with NOAA id {noaa_station_id} not found!")


# Read the file into memory for convenience
def load_file(filepath: str) -> dict:
    file_dict = {}
    with open(filepath) as surge_file:
        reader = csv.reader(surge_file, skipinitialspace=True)
        next(reader)  # skip header row
        for row in reader:
            #         TIME,    TIDE,      OB,   SURGE,    BIAS,      TWL
            # 202502181200,   2.275,9999.000,  -1.600,9999.000,   0.675
            date_str, tide_str, _, surge_str, bias_str, _ = row
            # Only the times on the hour have actual surge data.
            if int(date_str) % 100 != 0:
                continue
            if surge_str == _no_value:
                continue
            dt_utc = datetime.strptime(date_str, "%Y%m%d%H%M").replace(tzinfo=tz.utc)
            file_dict[dt_utc] = {
                "tide": float(tide_str),
                "surge": float(surge_str),
                "bias": float(bias_str) if bias_str != _no_value else None,
            }
    return file_dict


# Calculate anomaly/bias for this file, log it to the database and return it so it can be applied to surge values.  This is only needed for stations in the BiaslessStations list.
def calculate_bias(
    swmp_station: Station,
    timeline: Timeline,
    file_dict: dict,
    obs_tides: dict,
    minimum_deltas: int,
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

    deltas = []

    # Walk through the file contents. This will be in order of insert, which in this case is in tide time order.
    for dt_utc, rec in file_dict.items():
        # Note we don't have to convert the db's UTC into station zone, Python is smart.
        if timeline.contains(dt_utc) and dt_utc in obs_tides and dt_utc in tide_preds:
            delta = obs_tides[dt_utc] - (tide_preds[dt_utc] + rec["surge"])
            deltas.append(round(delta, 2))
        # since items() returns in key-insert order, we're done here
        elif dt_utc > timeline.end_dt:
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


# Update the Surge table obs column with any observations we have loaded.
def save_observations(swmp_station: Station, obs_tides: dict):

    # read all Surge records for tide times in past 24 hours from db where OBS is null
    end_dt = datetime.now(tz=swmp_station.time_zone)
    start_dt = end_dt - timedelta(days=1)

    qs = Surge.objects.filter(
        noaa_id=swmp_station.noaa_station_id,
        tide_time__range=(start_dt, end_dt),
        obs__isnull=True,
    ).order_by("tide_time")
    logger.info(
        f"There are {len(qs)} app_surge records with null obs for {swmp_station.noaa_station_id}"
    )

    # For each of those, if record exists in obs_dict, update the obs in the db.
    count = 0
    for rec in qs:
        # Note we don't have to convert the db's UTC into station zone, Python is smart.
        if rec.tide_time in obs_tides:
            rec.obs = obs_tides[rec.tide_time]
            rec.save()
            count += 1
    logger.info(f"updated obs value for {count} surge records")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(str(e))
