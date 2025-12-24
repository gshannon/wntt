import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from app import util
from app.hilo import Hilo, PredictedHighOrLow
from app.station import Station
from app.timeline import Timeline
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

"""
    Access NOAA tides & currents API interface for astronomical tide predictions. For Wells, see
        https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317
    For values, we request data in NAVD88 feet, and convert to MLLW feet using station configuration.
    For timezones, we request LST_LDT, or local standard time / local daylight time. This means the data
    comes the the correct local time, accounting for DST as appropriate.
"""
base_url = (
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=NOS.COOPS.TAC.WL"
    "&datum=NAVD&time_zone=lst_ldt&units=english&format=json"
)


def get_15m_astro_tides(station: Station, timeline: Timeline) -> dict:
    """
    Fetch astronomical tide level predictions for the desired timeline.

    Args:
        station (Station): the SWMP station
        timeline (Timeline): the timeline

    Returns:
        - dict of 15-min interval predictions for the past portion of the timeline. {dt: level}.
    """
    begin_date = timeline.start_dt.strftime("%Y%m%d")
    end_date = timeline.end_dt.strftime("%Y%m%d")
    pred_json = pull_data(station.noaa_station_id, "15", begin_date, end_date)
    return pred15_json_to_dict(pred_json, timeline, station)


def get_hilo_astro_tides(station: Station, timeline: Timeline) -> tuple[dict, dict]:
    """
    Fetch high/low astronomical tide predictions for the timeline. If the timeline starts in the past, it may
    include tide observations, and since we use predicted highs/lows to annotate observed highs/lows, we will
    need to pull in data for the day before the timeline to handle certain edge cases where a high or low
    occurs just before the start of the timeline.
    Args:
        station (Station): the SWMP station
        timeline (Timeline): the timeline

    Returns:
        dict of 15-min interval predictions for highs and lows only.
        {timeline_dt: PredictedHighOrLow}
    """

    preds_hilo_dict = {}

    request_start_dt = (
        timeline.start_dt - timedelta(days=1)
        if timeline.is_past(timeline.start_dt)
        else timeline.start_dt
    )
    start_date_str = request_start_dt.strftime("%Y%m%d")
    end_date_str = timeline.end_dt.strftime("%Y%m%d")

    future_preds_json = pull_data(
        station.noaa_station_id, "hilo", start_date_str, end_date_str
    )
    preds_hilo_dict = hilo_json_to_dict(station, future_preds_json, timeline.time_zone)

    return preds_hilo_dict


def pred15_json_to_dict(pred_json: list, timeline: Timeline, station: Station) -> dict:
    """
    Given a list of predictions at 15-min intervals like { "t": "2025-05-06 01:00", "v": "-3.624" }, return a
    sparse dict of {dt: value} for all values that exist in the requested timeline.
    Converts tide values to MLLW and datetimes from UTC to the station's timezone.
    """
    reg_preds_dict = {}  # {dt: value}
    if len(pred_json) == 0:
        return reg_preds_dict
    for pred in pred_json:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=station.time_zone)
        if timeline.contains(dt):
            val = pred["v"]
            reg_preds_dict[dt] = station.navd88_feet_to_mllw_feet(float(val))
    return reg_preds_dict


def hilo_json_to_dict(station: Station, hilo_json: list, tzone: ZoneInfo) -> dict:
    """
    Convert json returned from the api call into a dict of high or low data values.
    Args:
        hilo_json (string): json content: list of high/low predictions like
            {"t":"2027-01-01 04:25", "v":"-4.618", "type":"L"}
        tzone: timezone of the station

    Returns:
        A sparse dict of {timeline_dt: PredictedHighOrLow} for all values that
        exist in the requested timeline. Converts NAVD88 to MLLW.

    Raises:
        APIException: Invalid data from API
    """
    future_hilo_dict = {}
    if len(hilo_json) == 0:
        return future_hilo_dict
    for pred in hilo_json:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=tzone)
        # If we know the time of the last observation, use that as the cutoff instead of current time, since
        # there's a ~1 hour latency for observed data, and it's better to show the most accurate predictions
        # when we can. Remember hi/lo prediction dates are exact minutes, not aligned with 15-min intervals.
        val = pred["v"]
        if pred["type"] not in ["H", "L"]:
            logger.error(f"Unknown type {pred['type']} for date {dts}")
            raise APIException()
        hilo = Hilo.HIGH if pred["type"] == "H" else Hilo.LOW
        # Note the key is the 15-min time, to match the timeline. The actual datetime is in real_dt
        future_hilo_dict[util.round_to_quarter(dt)] = PredictedHighOrLow(
            station.navd88_feet_to_mllw_feet(float(val)), hilo, dt
        )

    return future_hilo_dict


def pull_data(noaa_station_id, interval, begin_date, end_date) -> list:
    """Call the tides&currents API, using:
        - time_zone=lst-ldt, which means local time, adjusted as appropriate for daylight savings time.
            This will always be relative to the timezone of the station, which will match the timeline.
        - datum=NAVD, which means the data will be in NAVD88 feet. We convert to MLLW feet. We don't ask for
            MLLW because that is a non-static standard, and the conversion will change when the new NTDE is published.

    Args:
        noaa_station_id (string): the NOAA station id, e.g. "8419317" for Wells
        interval (string): "15" for 15-min predictions, "hilo" for high/low predictions
        begin_date (string): YYYYMMDD
        end_date (string): YYYYMMDD

    Returns:
       Json list of dicts. Tide values are relative to NAVD88 and datetimes are in UTC.
        For interval=hilo:
            { "t": "2025-05-06 05:07", "v": "-3.630", "type": "L" },
        For interval=15:
            { "t": "2025-05-06 01:00", "v": "-3.624" },
    """
    url = f"{base_url}&interval={interval}&station={noaa_station_id}&begin_date={begin_date}&end_date={end_date}"

    try:
        response = requests.get(url)
    except Exception as e:
        raise APIException(f"Url: {url}", e)

    if response.status_code != 200:
        raise APIException(f"status {response.status_code} calling {url}")

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
