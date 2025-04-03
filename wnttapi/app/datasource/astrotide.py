from datetime import datetime
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
    We get the data in 15-minute intervals, in GMT.
"""

base_url = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=predictions&application=NOS.COOPS.TAC.WL"
            "&datum=MLLW&time_zone=GMT&units=english&format=json")

wells_station_id = "8419317"


def get_astro_tides(timeline: list) -> tuple[list,list,list]:
    """
    Load tide level predictions for the desired datetime range.
    Returns
    =======
        list of 15-min predictions corresponding to the requested timeline.  Values should never be None.
        list of datetime objects corresponding to the high and low tide times.
        list of 'H', 'L' or None corresponding to the high/low times list, indicating 'H' or 'L'.

    The returned prediction times are in 15-min intervals, but the highest and lowest value for any given tide come 
    from the high-low api call, which has 1-min granularity.  So we round the high-low data times to the closest 15-min 
    interval so they can be used on the graph, and marked as HIGH or lOW. So if the graph says the HIGH was X at 13:45, that
    means that X actually occurred between 13:38 and 13:52.  This is deemed preferable to simply showing the 15-min 
    values precisely, and not showing the actual HIGH and LOW tides, which are likely what the user is most interested in.

    Parameters
    ==========
    timeline : A list of timezone-aware datetimes representing the timeframe the user wants to see. It should
        match wall-clock for the timezone, in 15-min intervals, comprising one or more contiguous, complete days.
    """
    begin_date = timeline[0].strftime("%Y%m%d")
    end_date = timeline[-1].strftime("%Y%m%d")
    url15min = f"{base_url}&interval=15&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"
    urlhilo = f"{base_url}&interval=hilo&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"

    reg_preds_raw = pull_data(begin_date, end_date, url15min)
    reg_preds_dict = {}
    for pred in reg_preds_raw:
        dts = pred['t']
        val = pred['v']
        utc = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=tz.utc)
        dt = utc.astimezone(timeline[0].tzinfo)
        reg_preds_dict[dt] = round(float(val), 2)

    hilo_preds_raw = pull_data(begin_date, end_date, urlhilo)
    hilo_preds_dict = {}
    for pred in hilo_preds_raw:
        dts = pred['t']
        val = pred['v']
        typ = pred['type']  # should be 'H' or 'L'
        utc = datetime.strptime(dts, "%Y-%m-%d %H:%M").replace(tzinfo=tz.utc)
        dt = utc.astimezone(timeline[0].tzinfo)
        if typ not in ['H', 'L']:
            logger.error(f"Unknown type {typ} for date {dts}")
            raise APIException()
        # We round the actual high/low values to the closest 15-min interval so it aligns with our graph timeline
        hilo_preds_dict[util.round_to_quarter(dt)] = {'value': round(float(val), 2), 'type': typ}

    tide_values = []
    hilo_times = []
    hilo_values = []

    missing = 0
    for dt in timeline:

        if dt in hilo_preds_dict:
            stuff = hilo_preds_dict[dt]
            tide_values.append(stuff['value'])
            hilo_times.append(dt)
            hilo_values.append(stuff['type'])  # 'H' or 'L'

        else:
            if dt not in reg_preds_dict:
                tide_values.append(None)  # should never happen
                missing += 1
            else:
                tide_values.append(reg_preds_dict[dt])

    if missing:
        logger.error(f"Missing tide predictions: {missing}")

    return tide_values, hilo_times, hilo_values


def pull_data(begin_date, end_date, url) -> dict:
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

