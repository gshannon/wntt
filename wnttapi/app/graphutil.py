from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import APIException
from django.conf import settings
from datetime import date
import logging
from app.datasource import cdmo, astrotide as astro, surge as sg
from app import util
from . import tzutil as tz
from . import config as cfg

"""
Utility functions for plotting. There are some key concepts about time zones here that should be understood.
1. We want to show data in the the same time zone as that of the geographical area we are looking at. For now, 
that's US/Eastern, but in future it could be others. That means when DST starts, there is no 02:00, and
when DST ends, there are 2 01:00 hours. We build the timeline as so, to use as an index to give to the plotly library.
Plotly will insert a blank 2AM hour for DST start, and will not repeat 1AM hour when DST ends. There, we'll see
a break in the data, and the data zigzagging back over the same space for those 2 situations. 
2. All the data we get from CDMO is UTC minus 5 hours, as if it were Eastern Standard Time all year round. So those 
must be converted to local timezone after reading them.
3. We get astronomical tide prediction data from NOAA in GMT (UTC), via an api call. 
4. Surge data is in the form of a csv file which is refreshed 4 times per day by a cron job. Its timestamps are
all in UTC, so are converted to the local time zone.
"""

logger = logging.getLogger(__name__)
record_tide_title = f'Record Tide, {cfg.get_record_tide_date().strftime("%b %d, %Y")}'
mean_high_water_title = 'Mean High Water'
highest_annual_tide_title = 'Highest Annual Predicted Tide'
recorded_tide_title = 'Recorded Tide'
wspd_title = 'Average Wind Speed'
wgust_title = 'Wind Gust'
astro_tide_title = 'Predicted Tide'
past_surge_title = 'Storm Surge'
future_surge_title = 'Predicted Storm Surge'
future_tide_title = 'Predicted Storm Tide'
tide_graph_title = 'Wells Harbor Recorded Tides vs Predicted Tides'
wind_graph_title = 'Wells NERR Wind Speed and Direction'

# For now this is all we support, for Wells.  But someday if we support multiple reserves in multiple zones,
# there will be others to support.
time_zone = tz.eastern


def get_graph_data(start_date, end_date):
    """Takes a start date and end date and returns rendered html containing the line graph"""

    mhw = cfg.get_mean_high_water()
    validate_dates(start_date, end_date)
    timeline = util.build_timeline(start_date, end_date, time_zone)
    astro_tides = astro.get_astro_tides(timeline)
    hist_tides = cdmo.get_recorded_tides(timeline)
    past_surge, future_surge, future_tide = sg.get_surge_data(timeline, astro_tides, hist_tides)
    wind_speeds, wind_gusts, wind_dir, wind_dir_hover = cdmo.get_recorded_wind_data(timeline)
    record_tide = [cfg.get_record_tide()] + ([None] * (len(timeline) - 2)) + [cfg.get_record_tide()]
    mean_high_water = [mhw] + ([None] * (len(timeline) - 2)) + [mhw]
    highest_annual_predictions = get_annual_astro_high(timeline)

    (past_tl_index, future_tl_index) = util.get_timeline_info(timeline)
    start_date_str = timeline[0].strftime("%m/%d/%Y")
    end_date_str = timeline[-2].strftime("%m/%d/%Y")
    return {"timeline": timeline, "hist_tides": hist_tides,
            "astro_tides": astro_tides, "wind_speeds": wind_speeds, "wind_gusts": wind_gusts, "wind_dir": wind_dir,
            "wind_dir_hover": wind_dir_hover,  "record_tide": record_tide,
            "record_tide_title": f'{record_tide_title} ({cfg.get_record_tide():.2f})',
            "mean_high_water": mean_high_water,
            "mean_high_water_title": f'{mean_high_water_title} ({mhw:.2f})',
            "past_surge": past_surge, "future_surge": future_surge, "future_tide": future_tide,
            "highest_annual_predictions": highest_annual_predictions,
            "start_date": start_date_str, "end_date": end_date_str, "num_days": (end_date - start_date).days + 1,
            "past_tl_index": past_tl_index, "future_tl_index": future_tl_index
            }


def get_annual_astro_high(timeline) -> list:
    """Build data for the highest annual predicted tide plot. It could cross a year boundary.
    """
    time_count = len(timeline)
    high1 = cfg.get_astro_high_tide(timeline[0].year)

    # For annual high we will ignore the extra midnight time added to the timeline,
    # so it's timeline[-2] not timeline[-1]
    if timeline[0].year == timeline[-2].year:
        highs = [high1] + [None] * (time_count - 2) + [high1]
    else:
        # We're crossing a year boundary. Get the 2nd year's high.
        year2 = timeline[-1].year
        high2 = cfg.get_astro_high_tide(year2)
        # Figure out where in the index year 2 starts
        for ii, edt in enumerate(timeline):
            if edt.year == year2:
                break
        highs = [high1] + [None] * (ii - 2) + [high1, high2] + [None] * (time_count - ii - 2) + [high2]

    if len(highs) != time_count:
        raise APIException()
    return highs


def validate_dates(start, end):
    earliest_date = date(cfg.get_supported_years()[0], 1, 1)
    latest_date = date(cfg.get_supported_years()[-1], 12, 31)
    if start > latest_date or start < earliest_date or end > latest_date or end < earliest_date:
        logger.error(f"Invalidate range: {start} - {end} is not between {earliest_date} - {latest_date}")
        # This will return a code 400
        raise ValidationError(detail="Invalid date range")  # Override the default 'Invalid input'
    if end < start:
        logger.error(f"end_date {end} cannot be earlier than start_date {start}")
        raise ValidationError(detail="end date less than start date")
