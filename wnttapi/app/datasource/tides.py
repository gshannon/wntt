import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Tide:
    """A class to encapsulate a single water station reading for particular datetime.

    Args:
        temp_f (float): Temperature in Fahrenheit.
        clevel_nf (float): Corrected water level in NAVD88 feet. May NOT be None.
        clevel_raw (str): level in navd88 meters, exactly as received in the xml
        mllw_offset (float): NAVD88 to MLLW offset for the water station, used for datum conversion.
    """

    temp_f: float | None
    clevel_nf: float
    clevel_raw: str | None
    mllw_offset: float

    @property
    def corrected_mllw_feet(self) -> float:
        return self.navd88_to_mllw(self.clevel_nf)

    def navd88_to_mllw(self, navd88_value: float) -> float:
        return round(navd88_value + self.mllw_offset, 2)
