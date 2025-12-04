import json
import logging
from datetime import datetime, timedelta

import requests
from app import util
from app.station import Station
from app.timeline import Timeline
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

"""
    API interface for astronomical tide predictions in MLLW as provided by NWS. For Wells, see
        https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317
"""
base_url = (
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=NOS.COOPS.TAC.WL"
    "&datum=NAVD&time_zone=lst_ldt&units=english&format=json"
)


def get_astro_tides(
    station: Station, timeline: Timeline, max_observed_dt: datetime = None
) -> tuple[dict, dict]:
    """
    Fetch astronomical tide level predictions for the desired timeline. All values returned are MLLW. When we call the
    tides & currents API, we use:
        - time_zone=lst-ldt, which means Local Standard Time, as if there were no daylight savings time.
            This will always be relative to the timezone of the station, which will match the timeline.
        - datum=NAVD, which means the data will be in NAVD88 feet. We convert to MLLW feet. We don't ask for
            MLLW because that is a non-static standard, and the conversion will change when the new NTDE is published.

    Args:
        timeline (Timeline): the timeline
        max_observed_dt: the latest time in the timeline that has recorded tide data, or None for future timelines.
            When we have observed data, we annotate those as highs/lows, not the predicted values. This datetime is
            used to prevent requesting high/low predictions for times where we have observed data.

    Returns:
        tuple[dict, dict]:
        - dict of 15-min interval predictions for the past portion of the timeline. {dt: level}.
        - dict of 15-min interval predictions for highs and lows only.
          Structure is: {timeline_dt: {'real_dt': dt, 'value': level, 'type': 'H' or 'L'}}
          The time range will begin with the timeline start, or 15 minutes after the last max_observed_dt,
          which should be the most recent High or Low tide if we have a HiloTimeline. This means that the
          earliest predicted value returned could be in the past. This is desirable as there's generally
          a 30-90 minute latency between observation time and its availability from the API and we don't want gaps.
    """

    preds15_dict = {}
    preds_hilo_dict = {}

    # Part 1: pull 15-min predictions for the entire timeline. Even if we have a HiloTimeline for all future, where we show only
    begin_date = timeline.start_dt.strftime("%Y%m%d")
    end_date = timeline.end_dt.strftime("%Y%m%d")
    url15min = f"{base_url}&interval=15&station={station.noaa_station_id}&begin_date={begin_date}&end_date={end_date}"
    logger.debug(
        f"for timeline: {timeline.start_dt}-{timeline.end_dt}, url15min: {url15min}"
    )
    pred_json = pull_data(url15min)
    preds15_dict = pred15_json_to_dict(pred_json, timeline, station)

    # Part 2: For the the more precise High/Low values, we'll use a different API call.
    hilo_start_dt = (
        max_observed_dt + timedelta(minutes=15)
        if max_observed_dt is not None
        else timeline.start_dt
    )

    if hilo_start_dt <= timeline.end_dt:
        start_date = hilo_start_dt.strftime("%Y%m%d")
        end_date = timeline.end_dt.strftime("%Y%m%d")

        urlhilo = f"{base_url}&interval=hilo&station={station.noaa_station_id}&begin_date={start_date}&end_date={end_date}"
        logger.debug(f"for timeline: {start_date}-{end_date}, urlhilo: {urlhilo}")

        future_preds_json = pull_data(urlhilo)
        preds_hilo_dict = hilo_json_to_dict(
            station, future_preds_json, timeline, hilo_start_dt
        )

    return preds15_dict, preds_hilo_dict


def pred15_json_to_dict(pred_json: list, timeline: Timeline, station: Station) -> dict:
    """
    Given a list of predictions at 15-min intervals like { "t": "2025-05-06 01:00", "v": "-3.624" }, return a
    sparse dict of {dt: value} for all values that exist in the requested timeline. Converts NAVD88 to MLLW.
    """
    reg_preds_dict = {}  # {dt: value}
    for pred in pred_json:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline.time_zone)
        if timeline.contains(dt):
            val = pred["v"]
            reg_preds_dict[dt] = station.navd88_feet_to_mllw_feet(float(val))
    return reg_preds_dict


def hilo_json_to_dict(
    station: Station, hilo_json: list, timeline: Timeline, hilo_start_dt: datetime
) -> dict:
    """
    Convert json returned from the api call into a dict of high or low data values.
    Args:
        hilo_json (string): json content
        timeline (Timeline): the requested timeline.
        hilo_start_dt: Meant to be 15 min past the latest observed tide, or None if that doesn't
          exit. Data from times before this are ignored, even if part of timeline.

    Returns:
        dict: The key is the closest datetime that appears in the raw timeline, and the
        value is a dict describing the actual high or low values.
        Inner dict elements are "real_dt" (actual time), "value" (pred) and "type" ('H' or 'L').

    Raises:
        APIException: Invalid data from API

    """
    """
    Params:

    Given a list of high/low predictions like {"t":"2027-01-01 04:25", "v":"-4.618", "type":"L"}, return
    a sparse dict of {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}} for all values that
    exist in the requested timeline and are greater than the last observed tide time. Converts NAVD88 to MLLW.
    """
    future_hilo_dict = {}
    for pred in hilo_json:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline.time_zone)
        # If we know the time of the last observation, use that as the cutoff instead of current time, since
        # there's a ~1 hour latency for observed data, and it's better to show the most accurate predictions
        # when we can. Remember hi/lo prediction dates are exact minutes, not aligned with 15-min intervals.
        if hilo_start_dt <= dt <= timeline.end_dt:
            val = pred["v"]
            typ = pred["type"]  # should be 'H' or 'L'
            if typ not in ["H", "L"]:
                logger.error(f"Unknown type {typ} for date {dts}")
                raise APIException()
            # Note the key is the 15-min time, to match the timeline. The actual datetime is in real_dt
            future_hilo_dict[util.round_to_quarter(dt)] = {
                "real_dt": dt,
                "value": station.navd88_feet_to_mllw_feet(float(val)),
                "type": typ,
            }

    return future_hilo_dict


def pull_data(url) -> list:
    """Call the API and return the predictions as a json list of dictionaries in the form
    { "t": "2025-05-06 05:07", "v": "-3.630", "type": "L" },
    """
    try:
        response = requests.get(url)
    except Exception as e:
        logger.error(f"Url: {url} Response: {response}", exc_info=e)
        raise APIException()

    if response.status_code != 200:
        logger.error(f"status {response.status_code} calling {url}")
        raise APIException()

    try:
        return extract_json(response.text)
    except ValueError as e:
        logger.error(f"Error calling {url}: {e}")
        raise APIException(e)


def extract_json(raw) -> list:
    """Convert the response to a json list."""

    json_dict = json.loads(raw)
    # This is what content may look like if it's an invalid request.
    #  {"error": {"message":"No Predictions data was found. Please make sure the Datum input is valid."}}
    if "error" in json_dict:
        raise ValueError(json_dict)

    return json_dict["predictions"]
