import json
import logging
from datetime import datetime

import requests
from rest_framework.exceptions import APIException

from app import tzutil as tz
from app import util

logger = logging.getLogger(__name__)

"""
    API interface for astronomical tide predictions in MLLW as provided by NWS. For Wells, see
        https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317
"""
base_url = (
    "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=NOS.COOPS.TAC.WL"
    "&datum=NAVD&time_zone=lst_ldt&units=english&format=json"
)

wells_station_id = "8419317"


def get_astro_tides(timeline: list, last_recorded_dt: datetime) -> tuple[dict, dict]:
    """
    Fetch astronomical tide level predictions for the desired timeline.

    Returns:
        - {dt: val} predicted MLLW tides, using the 15-min interval API call
        - {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}} same, but for highs and lows only,
            and only after the last recorded dt, if any, using the high-low API call. The "real_dt" is the actual
            datetime of the high/low, likely not on a 15-min boundary.

    When we call the API, we use:
        - time_zone=lst-ldt, which means Local Standard Time, adjusted for daylight savings time. The timezone
            of the requested station will be used, and that should always match the timezone in the timeline,
            though there's no way to enforce that since the api call doesn't return the timezone.
        - datum=NAVD, which means the data will be in NAVD88 feet. We convert to MLLW feet. We don't ask for
            MLLW because that is a non-static standard, and the conversion will change when the new NTDE is published.

    The graph will be labeling recorded (past) tide data as high or low, so we don't include hi/low entries for past
    predictions. These dicts are dense -- only datetimes with data are included, and both dicts are keyed in
    chronological order.
    """
    begin_date = timeline[0].strftime("%Y%m%d")
    end_date = timeline[-1].strftime("%Y%m%d")
    url15min = f"{base_url}&interval=15&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"
    logger.debug(f"for timeline: {timeline[0]}-{timeline[-1]}, url15min: {url15min}")

    reg_preds_raw = pull_data(url15min)
    reg_preds_dict = {}  # {dt: value}
    for pred in reg_preds_raw:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline[0].tzinfo)
        # Only save data that's in the requested timeline
        if dt in timeline:
            val = pred["v"]
            reg_preds_dict[dt] = util.navd88_feet_to_mllw_feet(float(val))

    # If timeline is all in the past, we're done.
    future_hilo_dict = {}  # {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}}
    if timeline[-1] < tz.now(timeline[0].tzinfo):
        return reg_preds_dict, future_hilo_dict

    # We only want to ask for data we'll use, so get anything past the last recorded data time.
    cutoff = (
        util.round_up_to_quarter(last_recorded_dt)
        if last_recorded_dt is not None
        else timeline[0]
    )

    begin_date = cutoff.strftime("%Y%m%d")
    urlhilo = f"{base_url}&interval=hilo&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"
    logger.debug(f"for timeline: {timeline[0]}-{timeline[-1]}, urlhilo: {urlhilo}")

    hilo_preds_raw = pull_data(urlhilo)

    for pred in hilo_preds_raw:
        dts = pred["t"]
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline[0].tzinfo)
        # Only save data that's in the future AND in the requested timeline
        if dt >= cutoff and timeline[0] <= dt <= timeline[-1]:
            val = pred["v"]
            typ = pred["type"]  # should be 'H' or 'L'
            if typ not in ["H", "L"]:
                logger.error(f"Unknown type {typ} for date {dts}")
                raise APIException()
            # Note the key is the 15-min time, to match the timeline. The actual datetime is in real_dt
            future_hilo_dict[util.round_to_quarter(dt)] = {
                "real_dt": dt,
                "value": util.navd88_feet_to_mllw_feet(float(val)),
                "type": typ,
            }

    return reg_preds_dict, future_hilo_dict


def get_astro_highest(year) -> float:
    """Calls the external API for all hilo tides for a year, and returns the highest found."""
    begin_date = f"{year}0101"
    end_date = f"{year}1231"
    urlhilo = f"{base_url}&interval=hilo&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"
    logger.debug(f"for {year}, urlhilo: {urlhilo}")

    hilo_preds_raw = pull_data(urlhilo)
    highest = None

    for pred in hilo_preds_raw:
        val = util.navd88_feet_to_mllw_feet(float(pred["v"]))
        typ = pred["type"]  # should be 'H' or 'L'
        if typ not in ["H", "L"]:
            logger.error(f"Unknown type {typ}: {pred}")
            raise APIException()
        if typ == "H" and (highest is None or val > highest):
            highest = val

    return highest


def pull_data(url) -> dict:
    try:
        response = requests.get(url)
    except Exception as e:
        logger.error(f"Url: {url} Response: {response}", exc_info=e)
        raise APIException()

    if response.status_code != 200:
        logger.error(f"status {response.status_code} calling {url}")
        raise APIException()

    content = json.loads(response.text)
    # This is what content may look like if there's an error.  logger.info(content)
    #  {"error": {"message":"No Predictions data was found. Please make sure the Datum input is valid."}}
    if "error" in content:
        logger.error(f"error: {content.get('error', 'n/a')} calling [{url}]")
        raise APIException()

    return content["predictions"]
