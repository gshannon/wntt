from rest_framework.views import APIView, Response
from datetime import datetime
from . import graphutil as gr
import logging


logger = logging.getLogger(__name__)

UpgradeRequired = 426

class CreateGraphView(APIView):

    def post(self, request, format=None):
        # FYI, use the form request.META["HTTP_HOST"] to look at header fields.
        logger.info(f'params: {request.data}')

        start_date = datetime.strptime(request.data['start_date'], "%m/%d/%Y").date()
        end_date = datetime.strptime(request.data['end_date'], "%m/%d/%Y").date()

        # Gather all data needed for the graph and pass it back here
        graph_data = (gr.get_graph_data(start_date, end_date))
        return Response(data=graph_data)
