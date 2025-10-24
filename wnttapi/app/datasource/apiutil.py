import logging
from rest_framework.exceptions import APIException
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class APICall:
    def __init__(self, name: str, func, timeline, kwargs):
        self.name = name
        self.func = func
        self.timeline = timeline
        self.kwargs = kwargs
        self.data = None

    def setData(self, data: dict):
        self.data = data


def run_parallel(calls: list):
    # Call a list of APIs in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Use a dict comprehension to map active futures to calls
        future_to_call = {
            executor.submit(call.func, call.timeline, **call.kwargs): call
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
