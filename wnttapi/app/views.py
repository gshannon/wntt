from rest_framework.views import APIView, Response
from datetime import datetime
from . import graphutil as gr
import re
import logging


logger = logging.getLogger(__name__)

class CreateGraphView(APIView):

    def post(self, request, format=None):
        # FYI, use the form request.META["HTTP_HOST"] to look at header fields.
        # Obfuscate the IP address by replacing 1st 2 octets with ***
        pattern = r"(.*?\')(\d+\.\d+)(\.\d+.\d+\'.*)"
        logger.info(f'params: {re.sub(pattern, r'\1***.***\3', str(request.data))}')

        start_date = datetime.strptime(request.data['start_date'], "%m/%d/%Y").date()
        end_date = datetime.strptime(request.data['end_date'], "%m/%d/%Y").date()

        # Gather all data needed for the graph and pass it back here
        graph_data = (gr.get_graph_data(start_date, end_date))
        return Response(data=graph_data)
