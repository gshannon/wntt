#! /usr/bin/env python3
"""
This pulls XML data from CDMO for a given station and date range and dumps to stdout or a file.

This script requires these environment variables:
- CDMO_USER
- CDMO_PASSWORD
- WNTT (path to wntt root, the directory containing wnttapi/)
"""

import os
import sys
import argparse
from datetime import datetime


base = os.environ.get("WNTT")
sys.path.append(f"{base}/wnttapi")

from django import setup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

import app.datasource.cdmo as cdmo
from app import util
from app.station import get_station
from app.timeline import GraphTimeline, Timeline
from app import tzutil as tz


def text_error_check(non_text_node):
    message = non_text_node.text.strip()
    if len(message) > 0:
        print(f"Received unexpected message from CDMO: {message}")


Wells = "welinwq"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="output to this file (default is stdout)")
    parser.add_argument(
        "-s", "--station", default=Wells, help=f"station code (default {Wells})"
    )
    parser.add_argument("start_date", help="start date YYYY-mm-dd")
    parser.add_argument("end_date", help="end date YYYY-mm-dd")
    # parser.add_argument("params", nargs="?", help="comma-separated parameters to pull")

    args = parser.parse_args()
    station = get_station(args.station, data_dir=f"{base}/datamount/stations")

    do_water(args, station)
    # do_wind(args, station)


def do_wind(args, station):
    start_dt = datetime.strptime(args.start_date, "%Y-%m-%dT%H:%M").replace(
        tzinfo=tz.eastern
    )
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%dT%H:%M").replace(
        tzinfo=tz.eastern
    )
    print(f"Processing {start_dt} to {end_dt} ...", file=sys.stderr)
    timeline = Timeline(start_dt, end_dt)
    dict = cdmo.get_wind_data(station, timeline, True)
    print(dict)


def do_water(args, station):
    start_dt = datetime.strptime(args.start_date, "%Y-%m-%dT%H:%M").replace(
        tzinfo=tz.eastern
    )
    end_dt = datetime.strptime(args.end_date, "%Y-%m-%dT%H:%M").replace(
        tzinfo=tz.eastern
    )
    print(f"Processing {start_dt} to {end_dt} ...", file=sys.stderr)
    timeline = Timeline(start_dt, end_dt)

    # req_start_date, req_end_date = cdmo.compute_cdmo_request_dates(
    #     timeline.start_dt, timeline.end_dt
    # )

    water_dict = cdmo.get_water_data(station, timeline, useDb=True)
    obs_tides = water_dict.get(cdmo.Param.Tide, {})
    print(f"Got {len(obs_tides)} tide records from database", file=sys.stderr)

    water_dict = cdmo.get_water_data(station, timeline, useDb=False)
    obs_tides = water_dict.get(cdmo.Param.Tide, {})
    print(f"Got {len(obs_tides)} tide records from CDMO", file=sys.stderr)


if __name__ == "__main__":
    main()
