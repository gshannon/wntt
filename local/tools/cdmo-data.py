#! /usr/bin/env python3
"""
This pulls XML data from CDMO for a given station and date range and dumps to stdout or a file.

This script requires these environment variables:
- CDMO_USER
- CDMO_PASSWORD
- WNTT (path to wntt root, the directory containing wnttapi/)
"""

import sys
import os

base = os.environ.get("WNTT")
sys.path.append(f"{base}/wnttapi")
import argparse
from datetime import datetime

import app.datasource.cdmo as cdmo
import app.tzutil as tz
from app.timeline import GraphTimeline
from app import util


def text_error_check(non_text_node):
    message = non_text_node.text.strip()
    if len(message) > 0:
        print(f"Received unexpected message from CDMO: {message}")


Param = "Level"
Wells = "welinwq"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="output to this file (default is stdout)")
    parser.add_argument(
        "-s", "--station", default=Wells, help=f"station code (default {Wells})"
    )
    # these are positional:
    parser.add_argument("start_date", help="start date YYYY/mm/dd")
    parser.add_argument("end_date", help="end date YYYY/mm/dd")
    args = parser.parse_args()
    start = datetime.strptime(args.start_date, "%Y/%m/%d")
    end = datetime.strptime(args.end_date, "%Y/%m/%d")
    timeline = GraphTimeline(start, end, tz.eastern)
    req_start_date, req_end_date = cdmo.compute_cdmo_request_dates(
        timeline.get_min_with_padding(), timeline.get_max_with_padding()
    )

    soap_client = cdmo.get_soap_client()
    xml = soap_client.service.exportAllParamsDateRangeXMLNew(
        args.station, req_start_date, req_end_date, Param
    )
    if args.file:
        util.dump_xml(xml, args.file)
        print(f"Wrote {args.file}")
    else:
        print(bytes.fromhex(xml.hex()).decode("ASCII"))


if __name__ == "__main__":
    main()
