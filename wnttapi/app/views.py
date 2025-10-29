import hashlib
import logging
from datetime import datetime

from rest_framework.views import APIView, Response
from rest_framework.exceptions import NotAcceptable

from . import graphutil as gr
from . import swmp

logger = logging.getLogger(__name__)


# Try to get a param from the request. If not there, raise
# NotAcceptable (406), which in this context probably means
# the app is out of date and needs refreshed.
def get_param(data, param):
    if param in data:
        return data[param]
    logger.warning(f"Missing request parameter: {param}")
    raise NotAcceptable()


class LatestInfoView(APIView):
    def post(self, request, format=None):
        logger.info(f"LatestInfoView: {obfuscate(request.data)}")
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
        logger.info(f"CreateGraphView: {obfuscate(request.data)}")

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


def obfuscate(params):
    # Obfuscate the IP address with 1-way hash
    def hash(ip):
        return hashlib.sha256(ip.encode()).hexdigest()

    # Disabling this for now, as it does not seem necessary. We're doing nothing nefarious with the IPs, it's just
    # for counting distinct users.
    # return dict(map(lambda tup: (tup[0], hash(tup[1]) if tup[0] == 'ip' else tup[1]), params.items()))
    return params
