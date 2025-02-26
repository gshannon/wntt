from datetime import datetime, date, timedelta
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
    hist_tides = cdmo.get_recorded_tides(timeline)
    temps = cdmo.get_recorded_temps(timeline)

    timeline.reverse()
    wind_speeds.reverse()
    wind_dir.reverse()
    wind_gusts.reverse()
    hist_tides.reverse()
    temps.reverse()


    for (wind_speed, wind_gust, wind_dir, wind_time) in zip(wind_speeds, wind_gusts, wind_dir, timeline):
        if wind_speed is not None:
            break

    for (temp, temp_time) in zip(temps, timeline):
        if temp is not None:
            break

    # Tides are in reverse chronological order. Find the latest good value, and the the most recent value before that
    # to determine if the tide is rising or falling.
    tide = None
    tide_time = None
    direction = ''
    for (t, tt) in zip(hist_tides, timeline):
        if t is not None:
            if tide is None:
                tide = t
                tide_time = tt
            elif t != tide:
                direction = 'rising' if t < tide else 'falling'
                break
            
    logger.debug(f"ws: {wind_speed} [{ftime(wind_time)}], tide: {tide} [{ftime(tide_time)}], temp: {temp} [{ftime(temp_time)}]")
    return {
        'wind_speed': wind_speed,
        'wind_gust': wind_gust,
        'wind_dir': util.degrees_to_dir(wind_dir),
        'tide': f'{tide:.2f}',
        'tide_dir': direction,
        'temp': f'{util.centigrade_to_fahrenheit(temp):.1f}',
        'wind_time': ftime(wind_time),
        'tide_time': ftime(tide_time),
        'temp_time': ftime(temp_time),
    }

def ftime(dt):
    return dt.strftime('%b %d %Y %I:%M %p')