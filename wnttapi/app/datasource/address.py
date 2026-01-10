import logging
import os
import json

import requests
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

"""
    API interface for retrieving the lat/lon of an url-encoded physical address in the reserve area.
"""
base_url = f"https://geocode.maps.co/search?api_key={os.environ.get('GEOCODE_KEY')}"


def get_location(search: str) -> dict:
    """
    Call the geocode service with an address to look up, and get the lat/lon of that address, or error.
    All addresses are assumed to be in U.S.  They should include state.

    Args:
        search: encoded search string with an address in it

    Returns:
        dict with { 'lat': '<latitude>', 'lng', '<longitude>' }, or empty dict if address was not found
    """
    url = base_url + "&q=" + search
    logger.debug(f"url = {url}")

    try:
        response = requests.get(url)
    except Exception as e:
        e.add_note("Url: %s", url)
        raise e

    if response.status_code != 200:
        msg = "Got %d from %s" % (response.status_code, url)
        logger.error(msg)
        raise Exception(msg)

    try:
        jtext = json.loads(response.text)
        logger.debug(f"response text as json: {jtext}")
        return (
            {"lat": jtext[0]["lat"], "lng": jtext[0]["lon"]} if len(jtext) > 0 else {}
        )
    except ValueError as e:
        e.add_note("json.loads error on response from %s", url)
        raise e
