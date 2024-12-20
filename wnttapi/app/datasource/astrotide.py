from datetime import datetime
from app import tzutil as tz
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
            "&datum=MLLW&time_zone=GMT&units=english&interval=15&format=json")
wells_station_id = "8419317"


def get_astro_tides(timeline: list) -> list:
    """
    Load tide level predictions for the desired datetime range.
    Returns
    =======
        list of predictions corresponding to the requested timeline.  Values should never be None.

    Parameters
    ==========
    timeline : A list of timezone-aware datetimes representing the timeframe the user wants to see. It should
        match wall-clock for the timezone, in 15-min intervals, comprising one or more contiguous, complete days.
    """
    begin_date = timeline[0].strftime("%Y%m%d")
    end_date = timeline[-1].strftime("%Y%m%d")
    url = f"{base_url}&station={wells_station_id}&begin_date={begin_date}&end_date={end_date}"
    try:
        response = requests.get(url)
    except Exception as e:
        logger.error(f"Getting tide predictions", exc_info=e)
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

    preds = {}

    try:
        predictions = content["predictions"]

        found = 0
        for pred in predictions:
            dts = pred['t']
            val = pred['v']
            utc = tz.utc.localize(datetime.strptime(dts, "%Y-%m-%d %H:%M"))
            dt = utc.astimezone(timeline[0].tzinfo)
            preds[dt] = round(float(val), 2)
            found += 1

    except Exception as e:
        logger.error(f"Url: {url} Response: {response}", exc_info=e)
        raise APIException()

    data = []
    for dt in timeline:
        if dt not in preds:
            data.append(None)
        else:
            data.append(preds[dt])

    if len(timeline) > found:
        logger.error(f"Expected {len(timeline)} tide predictions, but got {found}")

    return data
