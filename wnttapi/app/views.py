import logging
import os
from datetime import datetime

from app.datasource import address
from rest_framework.exceptions import NotAcceptable
from rest_framework.views import APIView, Response

from . import graphutil as gr
from . import swmp
from . import station as stn

logger = logging.getLogger(__name__)
version = os.getenv("APP_VERSION", "set-me")


class StationSelectionView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        try:
            stations = stn.get_station_selection_data()
            return Response(data=stations)
        except Exception as e:
            log_exception(self.__class__.__name__, type(e).__name__, str(e), params)
            raise e


class StationDataView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        station_id = get_param(request.data, "station_id")
        try:
            station_data = stn.get_station_data(station_id)
            return Response(data=station_data)
        except Exception as e:
            log_exception(self.__class__.__name__, type(e).__name__, str(e), params)
            raise e


class LatestInfoView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        swmp_station_id = get_param(request.data, "station_id")
        station = stn.get_station(swmp_station_id)

        try:
            info = swmp.get_latest_conditions(station)
            return Response(data=info)
        except Exception as e:
            log_exception(self.__class__.__name__, type(e).__name__, str(e), params)
            raise e


class CreateGraphView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        start_date = datetime.strptime(
            get_param(request.data, "start"), "%m/%d/%Y"
        ).date()
        end_date = datetime.strptime(get_param(request.data, "end"), "%m/%d/%Y").date()
        hilo_mode = get_param(request.data, "hilo")
        station_id = get_param(request.data, "station_id")
        station = stn.get_station(station_id)

        try:
            # Gather all data needed for the graph and pass it back here
            graph_data = gr.get_graph_data(start_date, end_date, hilo_mode, station)
            return Response(data=graph_data)
        except Exception as e:
            log_exception(self.__class__.__name__, type(e).__name__, str(e), params)
            raise e


class AddressView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        search = get_param(request.data, "search")
        try:
            latlng = address.get_location(search)
            return Response(data=latlng)
        except Exception as e:
            log_exception(self.__class__.__name__, type(e).__name__, str(e), params)
            raise e


def log_exception(method, ename, message, params):
    logger.error("in %s, %s (%s) %s", method, ename, message, params)


def clean_params(data):
    return {k: v for k, v in data.items() if k != "signal"}


# Try to get a param from the request. If not there, raise
# NotAcceptable (406), which in this context probably means
# the app is out of date and needs refreshed.
def get_param(data, param):
    if param in data:
        return data[param]
    logger.warning("Missing request parameter %s", param)
    raise NotAcceptable()


# Verify that caller's release version matches ours.  If not, raise NotAcceptable
# which app should interpret as version out of date.
def verify_version(data):
    caller_version = get_param(data, "version")
    browser_id = data.get("bid", "unknown")
    if caller_version != version:
        msg = "Caller %s version %s does not match %s" % (
            browser_id,
            caller_version,
            version,
        )

        logger.warning(msg)
        raise NotAcceptable(msg)
