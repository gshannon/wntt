import logging
from abc import ABC
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Hilo(Enum):
    LOW = 1
    HIGH = 2


class HighOrLow(ABC):
    def __init__(self, value: float, hilo: Hilo):
        self.value = value
        if not isinstance(hilo, Hilo):
            raise ValueError("invalid hilo")
        self.hilo = hilo


class ObservedHighOrLow(HighOrLow):
    """Represents an observed High or Low Tide value

    Args:
        HighLowEvent (_type_): _description_
    """

    def __init__(self, value: float, hilo: Hilo):
        super().__init__(value, hilo)


class PredictedHighOrLow(HighOrLow):
    def __init__(self, value: float, hilo: Hilo, real_dt: datetime):
        super().__init__(value, hilo)
        self.real_dt = real_dt  # The actual time of the predicted event
