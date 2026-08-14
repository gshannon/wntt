import logging
from dataclasses import dataclass, fields

logger = logging.getLogger(__name__)


@dataclass
class Wind:
    """A class to encapsulate a single wind station reading for particular datetime.
    Args:
        speed_mph (float): Wind speed in mph.
        gust_mph (float): Wind gust speed in mph.
        direction_deg (int): Wind direction in degrees 0-360.
    """

    speed_mph: float
    gust_mph: float
    direction_deg: int

    def __post_init__(self):
        for fld in fields(self):
            if getattr(self, fld.name) is None:
                raise ValueError(f"Field '{fld.name}' cannot be None")

    @property
    def todict(self):
        return {
            "speed_mph": self.speed_mph,
            "gust_mph": self.gust_mph,
            "direction_deg": self.direction_deg,
        }
