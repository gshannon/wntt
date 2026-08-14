import logging
from dataclasses import dataclass, fields

logger = logging.getLogger(__name__)


@dataclass
class Tide:
    """A class to encapsulate a single water station reading for particular datetime.

    Args:
        temp_f (float): Temperature in Fahrenheit.
        corrected_nav_feet (float): Corrected water level in NAVD88 feet. May NOT be None.
        mllw_offset (float): NAVD88 to MLLW offset for the water station, used for datum conversion.
    """

    temp_f: float
    corrected_nav_feet: float
    mllw_offset: float

    @property
    def corrected_mllw_feet(self):
        return self.navd88_to_mllw(self.corrected_nav_feet)

    @property
    def todict(self):
        return {
            "temp_f": self.temp_f,
            "corrected_nav_feet": self.corrected_nav_feet,
            "corrected_mllw_feet": self.corrected_mllw_feet,
        }

    def nav_feet_equals(self, corrected_nav_feet: float) -> bool:
        if corrected_nav_feet is None and self.corrected_nav_feet is None:
            return True
        if corrected_nav_feet is None or self.corrected_nav_feet is None:
            return False
        return corrected_nav_feet == self.corrected_nav_feet

    def navd88_to_mllw(self, navd88_value):
        return round(navd88_value + self.mllw_offset, 2)

    def __post_init__(self):
        for fld in fields(self):
            if getattr(self, fld.name) is None:
                raise ValueError(f"Field '{fld.name}' cannot be None")
