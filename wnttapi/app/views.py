import logging
from datetime import datetime

from app.datasource import address
from rest_framework.exceptions import NotAcceptable
from rest_framework.views import APIView, Response

from . import config as cfg
from . import graphutil as gr
from . import swmp

logger = logging.getLogger(__name__)
version = cfg.get_version()


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
    ip = get_param(data, "ip")
    if caller_version != version:
        logger.warning(
            f"Caller {ip}: version {caller_version} does not match {version}"
        )
        raise NotAcceptable()


class LatestInfoView(APIView):
    def post(self, request, format=None):
        logger.info(f"LatestInfoView: {request.data}")
        verify_version(request.data)
        water_station = get_param(request.data, "water_station")
        weather_station = get_param(request.data, "weather_station")
        noaa_station_id = get_param(request.data, "noaa_station_id")

        info = swmp.get_latest_conditions(
            water_station, weather_station, noaa_station_id
        )
        return Response(data=info)


class CreateGraphView(APIView):
    def post(self, request, format=None):
        # FYI, use the form request.META["HTTP_HOST"] to look at header fields.
        logger.info(f"CreateGraphView: {request.data}")
        verify_version(request.data)
        start_date = datetime.strptime(
            get_param(request.data, "start_date"), "%m/%d/%Y"
        ).date()
        end_date = datetime.strptime(
            get_param(request.data, "end_date"), "%m/%d/%Y"
        ).date()
        water_station = get_param(request.data, "water_station")
        weather_station = get_param(request.data, "weather_station")
        noaa_station_id = get_param(request.data, "noaa_station_id")
        hilo_mode = get_param(request.data, "hilo_mode")

        # Gather all data needed for the graph and pass it back here
        graph_data = gr.get_graph_data(
            start_date,
            end_date,
            hilo_mode,
            water_station,
            weather_station,
            noaa_station_id,
        )
        return Response(data=graph_data)


class AddressView(APIView):
    def post(self, request, format=None):
        logger.info(f"AddressView: {request.data}")
        verify_version(request.data)
        search = get_param(request.data, "search")
        latlng = address.get_location(search)
        return Response(data=latlng)
