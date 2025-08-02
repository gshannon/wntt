import hashlib
import logging
from datetime import datetime

from rest_framework.views import APIView, Response

from . import graphutil as gr
from . import swmp

logger = logging.getLogger(__name__)


class LatestInfoView(APIView):
    def post(self, request, format=None):
        logger.info(f"LatestInfoView: {obfuscate(request.data)}")
        info = swmp.get_latest_conditions()
        return Response(data=info)


class CreateGraphView(APIView):
    def post(self, request, format=None):
        # FYI, use the form request.META["HTTP_HOST"] to look at header fields.
        logger.info(f"CreateGraphView: {obfuscate(request.data)}")

        start_date = datetime.strptime(request.data["start_date"], "%m/%d/%Y").date()
        end_date = datetime.strptime(request.data["end_date"], "%m/%d/%Y").date()
        hilo_mode = request.data["hilo_mode"]

        # Gather all data needed for the graph and pass it back here
        graph_data = gr.get_graph_data(start_date, end_date, hilo_mode)
        return Response(data=graph_data)


def obfuscate(params):
    # Obfuscate the IP address with 1-way hash
    def hash(ip):
        return hashlib.sha256(ip.encode()).hexdigest()

    # Disabling this for now, as it does not seem necessary. We're doing nothing nefarious with the IPs, it's just
    # for counting distinct users.
    # return dict(map(lambda tup: (tup[0], hash(tup[1]) if tup[0] == 'ip' else tup[1]), params.items()))
    return params
