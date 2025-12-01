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
        log_request("StationSelectionView", request.data)
        verify_version(request.data)
        stations = stn.get_station_selection_data()
        return Response(data=stations)


class StationDataView(APIView):
    def post(self, request, format=None):
        log_request("StationDataView", request.data)
        verify_version(request.data)
        station_id = get_param(request.data, "station_id")
        station_data = stn.get_station_data(station_id)
        return Response(data=station_data)


class LatestInfoView(APIView):
    def post(self, request, format=None):
        log_request("LatestInfoView", request.data)
        verify_version(request.data)
        swmp_station_id = get_param(request.data, "station_id")
        station = stn.get_station(swmp_station_id)

        info = swmp.get_latest_conditions(station)
        return Response(data=info)


class CreateGraphView(APIView):
    def post(self, request, format=None):
        # FYI, use the form request.META["HTTP_HOST"] to look at header fields.
        log_request("CreateGraphView", request.data)
        verify_version(request.data)
        start_date = datetime.strptime(
            get_param(request.data, "start_date"), "%m/%d/%Y"
        ).date()
        end_date = datetime.strptime(
            get_param(request.data, "end_date"), "%m/%d/%Y"
        ).date()
        hilo_mode = get_param(request.data, "hilo_mode")
        station_id = get_param(request.data, "station_id")
        station = stn.get_station(station_id)

        # Gather all data needed for the graph and pass it back here
        graph_data = gr.get_graph_data(start_date, end_date, hilo_mode, station)
        return Response(data=graph_data)


class AddressView(APIView):
    def post(self, request, format=None):
        log_request("AddressView", request.data)
        verify_version(request.data)
        search = get_param(request.data, "search")
        latlng = address.get_location(search)
        return Response(data=latlng)


def log_request(name, data):
    cleaned = {k: v for k, v in data.items() if k != "signal"}
    logger.info(f"{name}: {cleaned}")


# Try to get a param from the request. If not there, raise
# NotAcceptable (406), which in this context probably means
# the app is out of date and needs refreshed.
def get_param(data, param):
    if param in data:
        return data[param]
    logger.warning(f"Missing request parameter: {param}")
    raise NotAcceptable()


# Verify that caller's release version matches ours.  If not, raise NotAcceptable
# which app should interpret as version out of date.
def verify_version(data):
    caller_version = get_param(data, "app_version")
    ip = data.get("ip", "unknown")
    if caller_version != version:
        logger.warning(
            f"Caller {ip}: version {caller_version} does not match {version}"
        )
        raise NotAcceptable()
