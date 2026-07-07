import json
import logging
import os

import requests

from app import util

logger = logging.getLogger(__name__)
_request_timeout_seconds = 20

"""
    API interface for retrieving the lat/lon of an url-encoded physical address in the reserve area.
"""
base_url = "https://geocode.maps.co/search"


@util.request_logger
def get_location(search: str) -> dict:
    """
    Call the geocode service with an address to look up, and get the lat/lon of that address, or error.
    All addresses are assumed to be in U.S.  They should include state.

    Args:
        search: encoded search string with an address in it

    Returns:
        dict with { 'lat': '<latitude>', 'lng', '<longitude>' }, or empty dict if address was not found
    """

    params = {"api_key": os.environ.get("GEOCODE_KEY"), "q": search}

    response = requests.get(base_url, params=params, timeout=_request_timeout_seconds)
    response.raise_for_status()

    jtext = json.loads(response.text)
    logger.debug(f"response text as json: {jtext}")
    return {"lat": jtext[0]["lat"], "lng": jtext[0]["lon"]} if len(jtext) > 0 else {}
