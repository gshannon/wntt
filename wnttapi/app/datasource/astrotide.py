from datetime import datetime, time, timedelta
from app import tzutil as tz
from app import util
import requests
import json
import logging
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

"""
    API interface for astronomical tide predictions in MLLW as provided by NWS here for the Wells station:
        https://tidesandcurrents.noaa.gov/noaatidepredictions.html?id=8419317
"""

# TODO: use datum=NAVD and convert here.  Else app will be out of sync with NOAA temporarily when the site
# starts using the new NTDE. 
base_url = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=NOS.COOPS.TAC.WL"
            "&datum=MLLW&time_zone=lst_ldt&units=english&format=json")

wells_station_id = "8419317"


def get_astro_tides(timeline: list, last_recorded_dt: datetime) -> tuple[dict, dict]:
    """
    Fetch astronomical tide level predictions for the desired timeline.
    We get the data in 15-minute intervals, in lst_ldt (local time of station, adjusted for DST).

    Returns:
        - {dt: val} predicted tides, using the 15-min interval API call
        - {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}} same, but only for highs and lows only, 
            and only after the last recorded dt, if any, using the high-low API call. The "real_dt" is the actual 
            datetime of the high/low, likely not on a 15-min boundary.

    The graph will be labeling recorded (past) tide data as high or low, so we don't include hi/low entries for past 
    predictions. These dicts are dense -- only datetimes with data are included, and both dicts are keyed in 
    chronological order.
    """
    begin_date = timeline[0].strftime("%Y%m%d")
    end_date = timeline[-1].strftime("%Y%m%d")
    url15min = f"{base_url}&interval=15&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"
    urlhilo = f"{base_url}&interval=hilo&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"

    logger.debug(f"for timeline: {timeline[0]}-{timeline[-1]} astro_tides url15min: {url15min}")
    reg_preds_raw = pull_data(url15min)
    reg_preds_dict = {}  # {dt: value}
    for pred in reg_preds_raw:
        dts = pred['t']
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline[0].tzinfo)
        # Only save data that's in the requested timeline
        if dt in timeline:
            val = pred['v']
            reg_preds_dict[dt] = round(float(val), 2)

    hilo_preds_raw = pull_data(urlhilo)
    future_hilo_dict = {} # {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}}

    # Unless timeline is all in the past, get future HIGH/LOW predictions.
    if timeline[-1] < tz.now(timeline[0].tzinfo):
        return reg_preds_dict, future_hilo_dict
    
    cutoff = util.round_up_to_quarter(last_recorded_dt) if last_recorded_dt is not None else timeline[0]

    for pred in hilo_preds_raw:
        dts = pred['t']
        dt = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=timeline[0].tzinfo)
        # Only save data that's in the future AND in the requested timeline
        if dt >= cutoff and timeline[0] <= dt <= timeline[-1]:
            val = pred['v']
            typ = pred['type']  # should be 'H' or 'L'
            if typ not in ['H', 'L']:
                logger.error(f"Unknown type {typ} for date {dts}")
                raise APIException()
            # Note the key is the 15-min time, to match the timeline. The actual datetime is in real_dt
            future_hilo_dict[util.round_to_quarter(dt)] = {'real_dt': dt, 'value': round(float(val), 2), 'type': typ}

    return reg_preds_dict, future_hilo_dict

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
    if 'error' in content:
        logger.error(f"error: {content.get('error', 'n/a')} calling [{url}]")
        raise APIException()

    return content["predictions"]

