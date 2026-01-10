import logging
from abc import ABC
from datetime import datetime
from enum import Enum
from app import util

logger = logging.getLogger(__name__)

"""
A utility class for representing High and Low Tide events.
"""


class Hilo(Enum):
    LOW = 1
    HIGH = 2


class HighOrLow(ABC):
    """Abstract base class"""

    def __init__(self, value: float, hilo: Hilo):
        self.value = value
        if not isinstance(hilo, Hilo):
            raise util.InternalError(f"invalid hilo type: {type(hilo)}")
        self.hilo = hilo


class ObservedHighOrLow(HighOrLow):
    """Represents an observed High or Low Tide value -- data we got from CDMO."""

    def __init__(self, value: float, hilo: Hilo):
        super().__init__(value, hilo)

    def __str__(self):
        return f"{self.value} {self.hilo.name}"


class PredictedHighOrLow(HighOrLow):
    """Represents a predicted High or Low Tide value -- data we got from NOAA."""

    def __init__(self, value: float, hilo: Hilo, real_dt: datetime):
        super().__init__(value, hilo)
        self.real_dt = real_dt  # The actual time of the predicted event

    def __str__(self):
        return f"{self.value} {self.hilo.name} {self.real_dt.strftime('%Y-%m-%d %H:%M:%S')}"
