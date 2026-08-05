import functools
import logging
import os
from datetime import datetime

import sentry_sdk
from requests.exceptions import RequestException
from rest_framework.exceptions import APIException, NotAcceptable
from rest_framework.views import APIView, Response

from app.datasource import address

from . import graph as gr
from . import station as stn
from . import swmp
from . import tzutil as tz
from .models import Request, User, get_station

logger = logging.getLogger(__name__)
api_version = os.getenv("APP_VERSION", "set-me")


def endpoint_logger(func):
    # Decorator for error handling. We want to do stack traces only for "unexpected" exceptions.

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotAcceptable:
            # This is not a real error, it means caller's version is out of date.
            logger.info(f"NotAcceptable in {func.__qualname__}", stack_info=False)
            raise NotAcceptable from None
        except APIException as e:
            # General expected errors from SOAP calls or bad data from an API.
            logger.error(f"{type(e)} in {func.__qualname__}: {e}", stack_info=False)
            sentry_sdk.capture_exception(e)
            raise APIException() from None
        except RequestException as e:
            # These come from calls to requests.get(), which can fail.
            logger.error(
                f"{type(e)} in {func.__qualname__}: {e}",
                stack_info=False,
            )
            sentry_sdk.capture_exception(e)
            raise APIException() from None
        except Exception as e:
            # These are unexpected, so stack trace is ok
            logger.exception("Unexpected error in %s", func.__qualname__)
            sentry_sdk.capture_exception(e)
            raise APIException() from None

    return wrapper


class StationsView(APIView):
    @endpoint_logger
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)

        user_id = log_user(request.data.get("uid"))
        log_request(
            Request.Type.STATION,
            user_id,
            request.data.get("version"),
            request.data.get("screenWidth"),
        )
        return Response(data=stn.get_all_stations())


class LatestInfoView(APIView):
    @endpoint_logger
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        swmp_station_id = get_required(request.data, "station_id")
        station = stn.get_station(swmp_station_id)
        return Response(data=swmp.get_latest_conditions(station))


class CreateGraphView(APIView):
    @endpoint_logger
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        start_date = datetime.strptime(
            get_required(request.data, "start"), "%m/%d/%Y"
        ).date()
        end_date = datetime.strptime(
            get_required(request.data, "end"), "%m/%d/%Y"
        ).date()
        hilo_mode = get_required(request.data, "hilo")
        station_id = get_required(request.data, "station_id")
        station = stn.get_station(station_id)
        is_special = request.data.get("special", False)

        user_id = log_user(request.data.get("uid"))
        log_request(
            Request.Type.GRAPH,
            user_id,
            request.data.get("version"),
            request.data.get("screenWidth"),
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            hilo_mode=hilo_mode,
            customNav=request.data.get("customNav"),
        )

        # Gather all data needed for the graph and pass it back here
        graph_data = gr.get_graph_data(
            start_date, end_date, hilo_mode, station, is_special
        )
        return Response(data=graph_data)


class AddressView(APIView):
    @endpoint_logger
    def post(self, request, format=None):
        params = clean_params(request.data)
        logger.info("%s: %s", self.__class__.__name__, params)
        verify_version(request.data)
        search = get_required(request.data, "search")
        latlng = address.get_location(search)
        return Response(data=latlng)


def log_user(uid: str) -> int:
    if uid is None:
        logger.error("No uid in parameters!")
        return None
    try:
        id, created = User.objects.get_or_create(
            uuid=uid,
            # Use UTC since sqlite converts all times to UTC anyway.
            defaults={"uuid": uid, "created_at": tz.now(tz.utc)},
        )
        logger.debug(f"user created? {created} id: {id}")
        return id
    except Exception as exc:
        # Log but do not raise
        logger.exception(str(exc))
        sentry_sdk.capture_exception(exc)
        return None


def log_request(
    request_type: Request.Type,
    user_id: int,
    version: str,
    screenWidth: int,
    **kwargs,
):
    if user_id is None:
        return
    try:
        # Use UTC since sqlite converts all times to UTC anyway.
        now = tz.now(tz.utc)
        if request_type == Request.Type.STATION:
            Request.objects.create(
                user=user_id,
                when=now,
                type=request_type,
                version=version,
                screenWidth=screenWidth,
            )
        else:
            start_date = kwargs["start_date"]
            end_date = kwargs["end_date"]
            days = (end_date - start_date).days + 1
            db_station = get_station(kwargs["station_id"])

            Request.objects.create(
                user=user_id,
                when=now,
                type=request_type,
                station=db_station,
                version=version,
                start=start_date,
                days=days,
                hilo=kwargs["hilo_mode"],
                customNav=kwargs["customNav"],
                screenWidth=screenWidth,
            )

    except Exception as exc:
        # Log but do not raise
        logger.error(str(exc), stack_info=False)
        sentry_sdk.capture_exception(exc)


def clean_params(data):
    return {k: v for k, v in data.items() if k != "signal"}


# Try to get a param from the request. If not there, raise
# NotAcceptable (406), which in this context probably means
# the app is out of date and needs refreshed.
def get_required(data, param):
    if param in data:
        return data[param]
    logger.warning("Missing request parameter %s", param)
    raise NotAcceptable()


# Verify that caller's release version matches ours.  If not, raise NotAcceptable
# which app should interpret as version out of date.
def verify_version(data):
    caller_version = get_required(data, "version")
    if caller_version != api_version:
        raise NotAcceptable()
