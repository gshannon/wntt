import os
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)
dir_path = Path(__file__).parent
astro_file = dir_path / ".astro"


def read_highest_predicted() -> dict:
    """
    Read the .astro file and return a dictionary of year: tide.
    """
    logger.debug(f"Reading {astro_file}")
    data = {}
    if os.path.isfile(astro_file) and os.access(astro_file, os.R_OK):
        with open(astro_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                lst = re.findall("^(20\\d\\d):", line)
                if len(lst) == 1:
                    year = int(lst[0])
                    tide = float(line.split(":")[1])
                    data[year] = tide
    else:
        logger.warning(f"{astro_file} is not found or not readable.")
    return data


def write_highest_predicted(year, high):
    """
    Write the year and high tide to the .astro file.
    """
    # Get the directory of the current script
    logger.info(f"Writing {year}:{high} to {astro_file}")
    with open(astro_file, "a") as f:
        f.write(f"{year}:{high}\n")
