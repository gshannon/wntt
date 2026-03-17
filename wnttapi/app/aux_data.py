from datetime import datetime
from enum import Enum

"""Convenience classes to manage up to 6 different types of auxiliary data, keyed by datetime. Keys are kept short
to reduce the size of the json payload.
"""


class AuxDataType(Enum):
    OBSERVED_HILO = "HL"
    ASTRO_HILO = "AHL"
    OBSERVED_WIND_DIR = "WD"
    OBSERVED_WIND_DIR_STR = "WDS"
    FORECAST_WIND_DIR = "FWD"
    FORECAST_WIND_DIR_STR = "FWDS"


class AuxData:
    def __init__(self):
        self.data = {}

    def add(self, dt: datetime, auxType: AuxDataType, value):
        if dt not in self.data:
            self.data[dt] = {}
        self.data[dt][auxType.value] = value
