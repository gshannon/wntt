import logging
from dataclasses import dataclass

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
