import json
import logging
from datetime import datetime

import requests

from app import util
from app.hilo import Hilo, PredictedHighOrLow
from app.timeline import Timeline

logger = logging.getLogger(__name__)
_request_timeout_seconds = 20
_request_time_warning_seconds = 5

"""
    Access NOAA tides & currents API interface for astronomical tide predictions. For Wells, see
        https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317
    For values, we request data in NAVD88 feet, and convert to MLLW feet using station configuration.
    For timezones, we request lst_ldt, which returns it in the local time of the station as known to NOAA.
    Since the times come back as strings with no TZ component, we use the timezone of the requested timeline
    to convert the returned times into timezone-aware datetimes. Thus, for graphing, the requested timeline
    must match the actual timezone of the station in question, and there's no way to guarantee that herein.
"""
base_url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

base_params = {
    "product": "predictions",
    "application": "NOS.COOPS.TAC.WL",
    "datum": "NAVD",
    "time_zone": "lst_ldt",
    "units": "english",
    "format": "json",
}


def get_15m_astro_tides(
    noaa_station_id: str, timeline: Timeline, navd88_func: callable
) -> dict:
    """
    Fetch astronomical tide level predictions for the desired timeline.

    Args:
        station (Station): the SWMP station
        timeline (Timeline): the timeline

    Returns:
        - dict of 15-min interval predictions for the past portion of the timeline. {dt: level}.
    """
    pred_json = pull_data(noaa_station_id, "15", timeline)
    return pred15_json_to_dict(pred_json, timeline, navd88_func)


def get_hilo_astro_tides(
    noaa_station_id: str, timeline: Timeline, navd88_func: callable
) -> dict:
    """
    Fetch high/low astronomical tide predictions for the date range.
    Args:
        noaa_station_id: the 7-char station id, e.g. 8419317
        timeline: defines the data we want in time
        navd88_func: func to translate navd88 feet into mllw feet

    Returns:
        dict of 15-min interval predictions for highs and lows only. The PredictedHighOrLow object includes
            the exact datetime of the prediction.
        {timeline_dt: PredictedHighOrLow}
    """

    future_preds_json = pull_data(noaa_station_id, "hilo", timeline)
    return hilo_json_to_dict(future_preds_json, timeline, navd88_func)


def pred15_json_to_dict(
    pred_json: list, timeline: Timeline, navd88_func: callable
) -> dict:
    """
    Given a list of predictions at 15-min intervals like { "t": "2025-05-06 01:00", "v": "-3.624" }, return a
    sparse dict of {dt: value} for all values that exist in the requested timeline.
    Converts tide values to MLLW per the parameter and builds time-aware datetimes in the timeline's timezone.
    """
    reg_preds_dict = {}  # {dt: value}
    if len(pred_json) == 0:
        return reg_preds_dict
    for pred in pred_json:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline.time_zone)
        if timeline.contains(dt):
            val = pred["v"]
            reg_preds_dict[dt] = navd88_func(float(val))
    return reg_preds_dict


def hilo_json_to_dict(
    hilo_json: list, timeline: Timeline, navd88_func: callable
) -> dict:
    """
    Convert json returned from the api call into a dict of high or low data values.
    Args:
        hilo_json (string): json content: list of high/low predictions like
            {"t":"2027-01-01 04:25", "v":"-4.618", "type":"L"}
        tzone: timezone of the station

    Returns:
        A sparse dict of {timeline_dt: PredictedHighOrLow} for all values that exist in the requested timeline.
        Converts tide values to MLLW per the parameter and builds time-aware datetimes in the timeline's timezone.

    Raises:
        APIException: Invalid data from API
    """
    future_hilo_dict = {}
    if len(hilo_json) == 0:
        return future_hilo_dict
    for pred in hilo_json:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline.time_zone)
        if timeline.contains(dt):
            val = pred["v"]
            if pred["type"] not in ["H", "L"]:
                logger.error("Unknown type %s for date %s", pred["type"], dts)
                continue
            hilo = Hilo.HIGH if pred["type"] == "H" else Hilo.LOW
            # Note the key is the 15-min time, to match the timeline. The actual datetime is in real_dt
            future_hilo_dict[util.round_to_quarter(dt)] = PredictedHighOrLow(
                navd88_func(float(val)), hilo, dt
            )

    return future_hilo_dict


def pull_data(noaa_station_id: str, interval: str, timeline: Timeline) -> list:
    """Call the tides&currents API, using:
        - time_zone=lst_ldt
        - datum=NAVD, which means the data will be in NAVD88 feet.

        Example:
        https://api.tidesandcurrents.noaa.gov/api/prod/datagetter
            ?product=predictions
            &application=NOS.COOPS.TAC.WL
            &datum=NAVD
            &time_zone=lst_ldt
            &units=english
            &format=json
            &interval=15
            &station=8419317
            &begin_date=2026-06-27
            &end_date=2026-06-28

    Args:
        noaa_station_id (string): the NOAA station id, e.g. "8419317" for Wells
        interval (string): "15" for 15-min predictions, "hilo" for high/low predictions
        timeline: defines the date bounds of the data we want.

    Returns:
       Json list of dicts. Tide values are relative to NAVD88 and datetimes are in UTC.
        For interval=15:
            { "t": "2025-05-06 01:00", "v": "-3.624" },
        For interval=hilo:
            { "t": "2025-05-06 05:07", "v": "-3.630", "type": "L" },
    """
    params = {
        "interval": interval,
        "station": noaa_station_id,
        "begin_date": str(timeline.start_date),  # This yields "YYYY-dd-mm"
        "end_date": str(timeline.end_date),
    }

    try:
        response = requests.get(
            base_url, params=base_params | params, timeout=_request_timeout_seconds
        )
        seconds = response.elapsed.seconds
        if seconds > _request_time_warning_seconds:
            logger.warning(f"Call to {response.url} took {response.elapsed}")
        logger.debug(f"Elapsed={response.elapsed} from {response.url}")

    except Exception as e:
        e.add_note(f"Url: {response.url}")
        raise e

    if response.status_code != 200:
        raise Exception(f"status {response.status_code} calling {response.url}")

    try:
        return extract_json(response.text)
    except ValueError as e:
        e.add_note(f"Url: {response.url}")
        raise e


def extract_json(raw) -> list:
    """Convert the response to a json list."""

    json_dict = json.loads(raw)
    # This is what content may look like if it's an invalid request.
    #  {"error": {"message":"No Predictions data was found. Please make sure the Datum input is valid."}}
    if "error" in json_dict:
        raise Exception(f"found in returned json: {json_dict['error']}")

    return json_dict["predictions"]
