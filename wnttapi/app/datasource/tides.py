import logging
from datetime import datetime

from app import util

logger = logging.getLogger(__name__)


class Tides:
    """A container for a dict of tide objects keyed by datetime."""

    def __init__(self, mllw_offset: float):
        """Constructor

        Args:
            mllw_offset (float): The navd88-to-mllw offset for this collection of tides.
        """
        self.mllw_offset = mllw_offset
        self.data = {}

    def add_feet(
        self, dt: datetime, temp_f: float, mllw_feet: float, corrected_nav_feet: float
    ):
        """Add data to build a new Tide element for the collection. This is intended for use
        when reading water data from the database, and preparing it for use in the application.

        Args:
            dt (datetime): the datetime, in the timezone of the station
            temp_f (float): water temp in Fahrenheit
            mllw_feet (float): water level in MLLW feet -- DEPRECATED
            corrected_nav_feet (float): corrected water level in NAVD88 feet, may not be None
        """
        if corrected_nav_feet is None:
            raise util.InternalError("corrected_nav_feet may not be None")
        self.data[dt] = Tide(
            temp_f=temp_f,
            mllw_feet=mllw_feet,
            corrected_nav_feet=corrected_nav_feet,
            mllw_offset=self.mllw_offset,
        )

    # Use when reading from cdmo
    def add_meters(
        self,
        dt: datetime,
        temp_c: float,
        nav_meters: float,
        corrected_nav_meters: float,
    ):
        """Add data to build a new Tide element for the collection. This is intended for use
        when reading water data from CDMO, and preparing it for use in the application.

        Args:
            dt (datetime): the datetime, in the timezone of the station
            temp_c (float): water temp in Centigrade
            nav_meters (float): water level in NAVD88 meters (the "level" cdmo param) -- DEPRECATED
            corrected_nav_meters (float): corrected water level in NAVD88 meters (the "cLevel" cdmo param). Must
                not be None.
        """
        if corrected_nav_meters is None:
            raise util.InternalError("corrected_nav_meters may not be None")
        self.data[dt] = Tide(
            temp_f=util.centigrade_to_fahrenheit(temp_c)
            if temp_c is not None
            else None,
            mllw_feet=round(util.meters_to_feet(nav_meters) + self.mllw_offset, 2),
            corrected_nav_feet=util.meters_to_feet(corrected_nav_meters),
            mllw_offset=self.mllw_offset,
        )

    def getTide(self, dt: datetime):
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


class Tide:
    """A class to encapsulate a single water station reading for particular datetime."""

    def __init__(
        self,
        temp_f: float,
        # mllw_feet is deprecated -- will be removed shortly
        mllw_feet: float,
        corrected_nav_feet: float,
        mllw_offset: float,
    ):
        """Constructor

        Args:
            temp_f (float): Temperature in Fahrenheit.
            mllw_feet (float): Water level in MLLW feet - DEPRECATED
            corrected_nav_feet (float): Corrected water level in NAVD88 feet. May NOT be None.
            mllw_offset (float): NAVD88 to MLLW offset for the water station, used for datum conversion.
        """
        self.temp_f = temp_f
        self.mllw_feet = mllw_feet
        self.corrected_nav_feet = corrected_nav_feet
        self.mllw_offset = mllw_offset

    @property
    def corrected_mllw_feet(self):
        return round(self.corrected_nav_feet + self.mllw_offset, 2)

    def nav_feet_equals(self, corrected_nav_feet: float) -> bool:
        if corrected_nav_feet is None and self.corrected_nav_feet is None:
            return True
        if corrected_nav_feet is None or self.corrected_nav_feet is None:
            return False
        return corrected_nav_feet == self.corrected_nav_feet

    @property
    def dict(self):
        return {
            "temp_f": self.temp_f,
            "mllw_feet": self.mllw_feet,
            "corrected_nav_feet": self.corrected_nav_feet,
            "corrected_mllw_feet": self.corrected_mllw_feet,
        }
