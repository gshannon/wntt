#! /usr/bin/env python3

"""
This pulls NOAA's highest predicted tide relative to NAVD88 for a given station and year.
Use to populate annual_highs_navd88.json file.

Usage:

$ astro-highs.py -s <stationid> -y <year>

"""

from django.core.wsgi import get_wsgi_application
import argparse
import sys
import os

base = os.environ.get("WNTT")
sys.path.append(f"{base}/wnttapi")
os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings.dev"
import app.datasource.astrotide as astro

# This seems to necessary sometimes.
application = get_wsgi_application()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--station_id",
        required=True,
        help="NOAA station id",
    )
    parser.add_argument("-y", "--year", help="year", required=True, type=int)
    args = parser.parse_args()

    noaa_station_id = args.station_id
    year = args.year

    begin_date = f"{year}0101"
    end_date = f"{year}1231"
    urlhilo = f"{astro.base_url}&interval=hilo&station={noaa_station_id}&begin_date={begin_date}&end_date={end_date}"
    print(f"for {year}, urlhilo: {urlhilo}")

    hilo_json_dict = astro.pull_data(urlhilo)
    highest = find_highest_navd88(hilo_json_dict)
    print(highest)


def find_highest_navd88(hilo_json_dict) -> float:
    """Searches through the json and returns the highest NAVD88 high tide value found."""
    highest = None

    for pred in hilo_json_dict:
        val = round(float(pred["v"]), 2)
        typ = pred["type"]  # should be 'H' or 'L'
        if typ not in ["H", "L"]:
            print(f"Unknown type {typ}: {pred}")
            raise RuntimeError(f"Unknown type {typ} in {pred}")
        if typ == "H" and (highest is None or val > highest):
            highest = val

    return highest


if __name__ == "__main__":
    main()
