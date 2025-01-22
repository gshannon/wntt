from datetime import date, timedelta
import logging
from app.datasource import cdmo
from app import util
from . import tzutil as tz

time_zone = tz.eastern

logger = logging.getLogger(__name__)

def get_latest_info():
    """
    Pull the most recent wind, tide & temp readings from CDMO.
    """

    today = date.today()
    yesterday = today + timedelta(days=-1)
    timeline = util.build_timeline(yesterday, today, time_zone)

    wind_speeds, wind_gusts, wind_dir, _ = cdmo.get_recorded_wind_data(timeline)
    wind_speeds.reverse()
    wind_dir.reverse()
    wind_gusts.reverse()
    for (wind_speed, wind_gust, wind_dir) in zip(wind_speeds, wind_gusts, wind_dir):
        if wind_speed is not None:
            break

    hist_tides = cdmo.get_recorded_tides(timeline)
    hist_tides.reverse()
    for tide in hist_tides:
        if tide is not None:
            break

    temps = cdmo.get_recorded_temps(timeline)
    temps.reverse()
    for temp in temps:
        if temp is not None:
            break

    logger.debug(f"wind_speed: {wind_speed}, wind_gust: {wind_gust}, wind_dir: {wind_dir}, tide: {tide}")
    wd = util.degrees_to_dir(wind_dir)
    return {
        'wind_speed': wind_speed,
        'wind_gust': wind_gust,
        'wind_dir': wd,
        'tide': f'{tide:.2f}',
        'temp': f'{util.centigrade_to_fahrenheit(temp):.1f}'
    }

