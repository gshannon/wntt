import functools
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any, ParamSpec, TypeVar

import sentry_sdk
from requests.exceptions import RequestException
from rest_framework.exceptions import APIException, NotAcceptable
from rest_framework.request import Request as DrfRequest
from rest_framework.response import Response
from rest_framework.views import APIView

from app.datasource import address

from . import graph as gr
from . import station as stn
from . import swmp
from . import tzutil as tz
from .models import Request, User, get_station

logger = logging.getLogger(__name__)
api_version = os.getenv("APP_VERSION", "set-me")

P = ParamSpec("P")
R = TypeVar("R")


def endpoint_logger(func: Callable[P, R]) -> Callable[P, R]:
    # Decorator for error handling. We want to do stack traces only for "unexpected" exceptions.

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
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
    def post(self, request: DrfRequest) -> Response:
        data = object_body(request)
        logger.info("%s: %s", self.__class__.__name__, data)
        verify_version(data)

        user = log_user(data.get("uid", None))
        log_request(
            Request.Type.STATION,
            user,
            get_required(data, "version"),
            data.get("screenWidth"),
        )
        return Response(
            data={
                "stations": stn.get_all_stations(),
                "banner": os.getenv("APP_BANNER", "").strip(),
            }
        )


class LatestInfoView(APIView):
    @endpoint_logger
    def post(self, request: DrfRequest, format: str | None = None) -> Response:
        data = object_body(request)
        logger.info("%s: %s", self.__class__.__name__, data)
        verify_version(data)
        swmp_station_id = get_required(data, "station_id")
        station = stn.get_station(swmp_station_id)
        conditions = swmp.get_latest_conditions(station)
        return Response(data=asdict(conditions))


class CreateGraphView(APIView):
    @endpoint_logger
    def post(self, request: DrfRequest, format: str | None = None) -> Response:
        data = object_body(request)
        logger.info("%s: %s", self.__class__.__name__, data)
        verify_version(data)
        start_date = datetime.strptime(get_required(data, "start"), "%m/%d/%Y").date()  # noqa
        end_date = datetime.strptime(get_required(data, "end"), "%m/%d/%Y").date()  # noqa
        hilo_mode = get_required(data, "hilo")
        station_id = get_required(data, "station_id")
        station = stn.get_station(station_id)
        is_special = data.get("special", False)

        user_id = log_user(data.get("uid", None))
        log_request(
            Request.Type.GRAPH,
            user_id,
            get_required(data, "version"),
            data.get("screenWidth"),
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            hilo_mode=hilo_mode,
            customNav=data.get("customNav"),
        )

        # Gather all data needed for the graph and pass it back here
        graph_data: gr.GraphData = gr.get_graph_data(
            start_date, end_date, hilo_mode, station, is_special
        )
        return Response(data=asdict(graph_data))


class AddressView(APIView):
    @endpoint_logger
    def post(self, request: DrfRequest, format: str | None = None) -> Response:
        data = object_body(request)
        logger.info("%s: %s", self.__class__.__name__, data)
        verify_version(data)
        search = get_required(data, "search")
        latlng = address.get_location(search)
        return Response(data=latlng)


def log_user(uid: str | None) -> User | None:
    if uid is None:
        logger.error("No uid in parameters!")
        return None
    try:
        user, created = User.objects.get_or_create(
            uuid=uid,
            # Use UTC since sqlite converts all times to UTC anyway.
            defaults={"uuid": uid, "created_at": datetime.now(tz.utc)},
        )
        logger.debug(f"user created? {created} id: {id}")
        return user
    except Exception as exc:
        # Log but do not raise
        logger.exception(str(exc))
        sentry_sdk.capture_exception(exc)
        return None


def object_body(request: DrfRequest) -> dict[str, Any]:
    """These endpoints only accept a JSON object body; DRF types request.data as dict | list."""
    data = request.data
    if not isinstance(data, dict):
        raise NotAcceptable()
    return data


def log_request(
    request_type: Request.Type,
    user: User | None,
    version: str,
    screenWidth: int | None,
    **kwargs: Any,
) -> None:
    if user is None:
        return
    try:
        # Use UTC since sqlite converts all times to UTC anyway.
        now = datetime.now(tz.utc)
        if request_type == Request.Type.STATION:
            Request.objects.create(
                user=user,
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
                user=user,
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

    except Exception as exc:  # noqa
        # Log but do not raise
        logger.error(str(exc), stack_info=False)
        sentry_sdk.capture_exception(exc)


# Try to get a param from the request. If not there, raise
# NotAcceptable (406), which in this context probably means
# the app is out of date and needs refreshed.
def get_required(data: Mapping[str, Any], param: str) -> Any:
    if param in data:
        return data[param]
    logger.warning("Missing request parameter %s", param)
    raise NotAcceptable()


# Verify that caller's release version matches ours.  If not, raise NotAcceptable
# which app should interpret as version out of date.
def verify_version(data: Mapping[str, Any]) -> None:
    caller_version = get_required(data, "version")
    if caller_version != api_version:
        raise NotAcceptable()
