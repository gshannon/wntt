import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.station import Station
from app.timeline import Timeline
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

"""Support for running multiple API calls in parallel."""


class APICall:
    def __init__(self, name: str, func: callable, station: Station, timeline: Timeline):
        self.name = name
        self.func = func
        self.station = station
        self.timeline = timeline
        self.data = None

    def setData(self, data: dict):
        self.data = data


def run_parallel(calls: list):
    # Call a list of APICall objects in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Use a dict comprehension to map active futures to calls
        future_to_call = {
            executor.submit(call.func, call.station, call.timeline): call
            for call in calls
        }
        for future in as_completed(future_to_call):
            call = future_to_call[future]
            try:
                logger.debug(f"waiting on {call.name}...")
                call.setData(future.result())
            except Exception as exc:
                logger.error("%r generated an exception: %s" % (call.name, exc))
                raise APIException(f"Getting {call.name}: {exc}")
            else:
                logger.debug(f"Got data back from {call.name}")
