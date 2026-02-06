import logging
import os
from datetime import datetime

import sentry_sdk
from app.datasource import address
from rest_framework.exceptions import APIException, NotAcceptable
from rest_framework.views import APIView, Response

from . import graphutil as gr
from . import station as stn
from . import swmp
from . import tzutil as tz
from .models import Request, User

logger = logging.getLogger(__name__)
version = os.getenv("APP_VERSION", "set-me")


class StationsView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)

        user_id = log_user(request.data)
        log_request(request.data, user_id, Request.Type.STATION, None, None, None)

        try:
            stations = stn.get_all_stations()
            return Response(data=stations)
        except NotAcceptable as exc:
            logger.warning(f"NotAcceptable {params}")
            raise exc
        except Exception as exc:
            logger.exception(str(exc))
            sentry_sdk.capture_exception(exc)
            raise APIException(str(exc))


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
        except NotAcceptable as exc:
            logger.warning(f"NotAcceptable {params}")
            raise exc
        except Exception as exc:
            logger.exception(str(exc))
            sentry_sdk.capture_exception(exc)
            raise APIException(str(exc))


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
        days = (end_date - start_date).days + 1
        db_station = Request.get_station(station_id)

        user_id = log_user(request.data)
        log_request(
            request.data, user_id, Request.Type.GRAPH, db_station, hilo_mode, days
        )

        try:
            # Gather all data needed for the graph and pass it back here
            graph_data = gr.get_graph_data(start_date, end_date, hilo_mode, station)
            return Response(data=graph_data)
        except NotAcceptable as exc:
            logger.warning(f"NotAcceptable {params}")
            raise exc
        except Exception as exc:
            logger.exception(str(exc))
            sentry_sdk.capture_exception(exc)
            raise APIException(str(exc))


class AddressView(APIView):
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        search = get_param(request.data, "search")
        try:
            latlng = address.get_location(search)
            return Response(data=latlng)
        except NotAcceptable as exc:
            logger.warning(f"NotAcceptable {params}")
            raise exc
        except Exception as exc:
            logger.exception(str(exc))
            sentry_sdk.capture_exception(exc)
            raise APIException(str(exc))


def log_user(data) -> int:
    if "uid" not in data:
        logger.debug("No uid in parameters")
        return None
    try:
        id, created = User.objects.get_or_create(
            uuid=data["uid"],  # Lookup criteria (must be unique)
            defaults={"uuid": data["uid"], "created_at": tz.now(tz.eastern)},
        )
        logger.debug(f"user created? {created} id: {id}")
        return id
    except Exception as exc:
        logger.exception(str(exc))
        sentry_sdk.capture_exception(exc)
        return None


def log_request(
    data: dict,
    user_id: int,
    request_type: Request.Type,
    station: Request.Station,
    hilo_mode: bool,
    days: int,
):
    if user_id is None:
        return
    try:
        obj = Request.objects.create(
            user=user_id,
            when=tz.now(tz.eastern),
            station=station,
            type=request_type,
            version=get_param(data, "version"),
            hilo=hilo_mode,
            days=days,
        )
        logger.debug("request created")
        logger.debug(obj)

    except Exception as exc:
        logger.exception(str(exc))
        sentry_sdk.capture_exception(exc)


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
