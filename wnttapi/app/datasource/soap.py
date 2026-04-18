import logging
import os
import time
from suds.client import Client
from suds.transport.https import HttpAuthenticated, HttpTransport

logger = logging.getLogger(__name__)
CDMO_WSDL = "https://cdmo.baruch.sc.edu/webservices2/requests.cfc?wsdl"
TIMEOUT_SEC = 300


class CustomTransport(HttpAuthenticated):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        HttpAuthenticated.__init__(self, username=username, password=password)

    def open(self, request):
        request.headers["authorization"] = f"Basic {self._basic_auth()}"
        return HttpTransport.open(self, request)

    def _basic_auth(self):
        import base64

        credentials = f"{self.username}:{self.password}"
        return base64.b64encode(credentials.encode("utf-8")).decode("utf-8")


class SoapClient:
    """Singleton class to hold the suds Client object, since creating it is expensive and seems to cause CDMO to reject the user/password if done on every request. This is a workaround until that issue is resolved."""

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            user_name = os.environ.get("CDMO_USER", None)
            password = os.environ.get("CDMO_PASSWORD", None)
            transport = (
                CustomTransport(user_name, password) if user_name and password else None
            )
            start_time = time.time()
            try:
                if transport is not None:
                    logger.info(f"Creating Client with username {user_name}")
                    cls._client = Client(
                        CDMO_WSDL,
                        retxml=True,
                        transport=transport,
                    )
                else:
                    logger.info("Creating Client with no transport")
                    cls._client = Client(
                        CDMO_WSDL,
                        retxml=True,
                    )
            except Exception as exc:
                elapsed_sec = time.time() - start_time
                msg = f"Error creating Client, time {round(elapsed_sec, 2)} sec: {str(exc)}"
                # unfortunately this happens often & we don't want to clutter the sentry logs
                if "urlopen" in str(exc):
                    logger.warning(msg)
                else:
                    logger.error(msg)
                raise exc
            # This is the only way to override the default 90 sec.  Doesn't work in constructor.
            cls._client.set_options(timeout=TIMEOUT_SEC)
            elapsed_sec = time.time() - start_time
            if elapsed_sec > 5:
                logger.info(f"Created Client object in {round(elapsed_sec, 2)} sec")
            else:
                logger.debug(f"Created Client object in {round(elapsed_sec, 2)} sec")
        return cls._client
