import logging
import os
import json

import requests
import traceback

logger = logging.getLogger(__name__)
_request_timeout_seconds = 20

"""
    API interface for retrieving the lat/lon of an url-encoded physical address in the reserve area.
"""
base_url = "https://geocode.maps.co/search"


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

    try:
        response = requests.get(
            base_url, params=params, timeout=_request_timeout_seconds
        )
        logger.debug(f"Elapsed={response.elapsed} from {response.url}")
    except Exception as e:
        e.add_note("Url: %s", response.url)
        exc_desc = "".join(traceback.format_exception_only(type(e), e)).rstrip()
        logger.error(exc_desc)
        raise e

    if response.status_code != 200:
        msg = "Got %d from %s" % (response.status_code, response.url)
        logger.error(msg)
        raise Exception(msg)

    try:
        jtext = json.loads(response.text)
        logger.debug(f"response text as json: {jtext}")
        return (
            {"lat": jtext[0]["lat"], "lng": jtext[0]["lon"]} if len(jtext) > 0 else {}
        )
    except ValueError as e:
        e.add_note("json.loads error on response from %s", response.url)
        raise e
