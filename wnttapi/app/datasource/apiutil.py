import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.station import Station

logger = logging.getLogger(__name__)

"""Support for running multiple API calls in parallel."""


class APICall:
    def __init__(self, name: str, func: callable, station: Station, *args):
        self.name = name
        self.func = func
        self.station = station
        self.args = args
        self.data = None

    def setData(self, data: dict):
        self.data = data


def run_parallel(calls: list):
    # Call a list of APICall objects in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Use a dict comprehension to map active futures to calls
        future_to_call = {
            executor.submit(call.func, call.station, *call.args): call for call in calls
        }
        for future in as_completed(future_to_call):
            call = future_to_call[future]
            logger.debug(f"waiting on {call.name}...")
            call.setData(future.result())
