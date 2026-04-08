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

base = os.environ.get("WNTT")
sys.path.append(f"{base}/wnttapi")
import argparse
from datetime import datetime

import app.datasource.cdmo as cdmo
from app import util


def text_error_check(non_text_node):
    message = non_text_node.text.strip()
    if len(message) > 0:
        print(f"Received unexpected message from CDMO: {message}")


# Param = "Level"
Wells = "welinwq"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="output to this file (default is stdout)")
    parser.add_argument(
        "-s", "--station", default=Wells, help=f"station code (default {Wells})"
    )
    parser.add_argument("start_date", help="start date YYYY-mm-dd")
    parser.add_argument("end_date", help="end date YYYY-mm-dd")
    parser.add_argument("params", nargs="?", help="comma-separated parameters to pull")
    args = parser.parse_args()
    start = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    print(f"Processing {start} to {end} ...", file=sys.stderr)
    # timeline = GraphTimeline(start, end, tz.eastern)
    # req_start_date, req_end_date = cdmo.compute_cdmo_request_dates(
    #     timeline.get_min_with_padding(), timeline.get_max_with_padding()
    # )

    xml = cdmo.SoapClient.get_client().service.exportAllParamsDateRangeXMLNew(
        args.station, start, end, args.params
    )
    # "Level,Wspd,MaxWspd,Wdir"
    if args.file:
        util.dump_xml(xml, args.file)
        print(f"Wrote {args.file}")
    else:
        print(bytes.fromhex(xml.hex()).decode("ASCII"))


if __name__ == "__main__":
    main()
