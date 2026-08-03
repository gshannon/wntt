import logging
from datetime import datetime

from app import util

logger = logging.getLogger(__name__)


class Winds:
    """A container for a dict of Wind objects keyed by datetime."""

    def __init__(self):
        self.data = {}

    def add(
        self,
        dt: datetime,
        speed_mph: float,
        gust_mph: float,
        direction_deg: int,
    ):
        """Add data to build a new Wind element for the collection.

        Args:
            dt (datetime): the datetime, in the timezone of the station
            speed_mph (float): wind speed in miles per hour
            gust_mph (float): wind gust speed in miles per hour
            direction_deg (int): wind direction in degrees (0-360)
        """
        if dt is None or speed_mph is None or gust_mph is None or direction_deg is None:
            raise util.InternalError(
                "dt, speed_mph, gust_mph, and direction_deg may not be None"
            )
        if direction_deg < 0 or direction_deg > 360:
            raise util.InternalError(
                f"direction_deg must be between 0 and 360, got {direction_deg}"
            )
        self.data[dt] = Wind(
            speed_mph=speed_mph, gust_mph=gust_mph, direction_deg=direction_deg
        )

    def getWind(self, dt: datetime):
        return self.data.get(dt, None)

    def contains(self, dt: datetime):
        return dt in self.data

    @property
    def length(self):
        return len(self.data)

    def sort(self):
        if len(self.data) > 0:
            ordered = dict(sorted(self.data.items(), key=lambda x: x[0]))
            self.data = ordered


class Wind:
    """A class to encapsulate a single wind station reading for particular datetime."""

    def __init__(
        self,
        speed_mph: float,
        gust_mph: float,
        direction_deg: int,
    ):
        """Constructor

        Args:
            speed_mph (float): Wind speed in mph.
            gust_mph (float): Wind gust speed in mph.
            direction_deg (int): Wind direction in degrees 0-360.
        """
        self.speed_mph = speed_mph
        self.gust_mph = gust_mph
        self.direction_deg = direction_deg
