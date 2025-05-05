import logging
from datetime import date, timedelta

from rest_framework.exceptions import APIException, ValidationError

from app import util
from app.datasource import astrotide as astro
from app.datasource import cdmo
from app.datasource import surge as sg

from . import config as cfg
from . import tzutil as tz

"""
Utility functions for plotting. 

We want to show data in the the same time zone as that of the geographical area we are looking at. For now, 
that's US/Eastern, but in future it could be others. That means when DST starts, there is no 02:00, and
when DST ends, there are 2 01:00 hours. We build the timeline as so, to use as an index to give to the plotly library.
Plotly will insert a blank 2AM hour for DST start, and will not repeat 1AM hour when DST ends. There, we'll see
a break in the data, and the data zigzagging back over the same space for those 2 situations. 

For most data, we build the full data arrays here which means passing lots of None values to the app. This
increases the size of the data passed to the app, but it offloads the work of building the data arrays to this
server instead of the browser. If this is ever considered to be a bad tradeoff, that can be changed. However, passing
dictionaries of data keyed on datetime objects would entail a lot of bandwidth also -- many copies of the same datetimes.
"""

logger = logging.getLogger(__name__)
record_tide_title = f"Record Tide, {cfg.get_record_tide_date().strftime('%b %d, %Y')}"

# For now this is all we support, for Wells.  But someday if we support multiple reserves in multiple zones,
# there will be others to support, so we'll probably pull this from the http client request.
time_zone = tz.eastern


def get_graph_data(start_date, end_date):
    """Takes a start date and end date and returns rendered html containing the line graph"""

    validate_dates(start_date, end_date)

    # In the timeline, we will build data for entire dates between start and end, inclusive. This adds a single
    # datetime at midnight of the following day, so the graph looks tidy on the right side.
    timeline = util.build_graph_timeline(start_date, end_date, time_zone)

    # Retrieve all data from external sources. All these dicts are dense -- they only have entries for actual data,
    # not None. They are keyed by the datetime that matches the timeline.
    obs_dict = cdmo.get_recorded_tides(timeline)
    max_observed_dt = max(obs_dict) if len(obs_dict) > 0 else None
    obs_hilo_dict = cdmo.find_hilos(timeline, obs_dict)  # {dt: 'H' or 'L'}
    wind_dict = cdmo.get_recorded_wind_data(
        timeline
    )  # {dt: {speed, gust, dir, dir_str}}
    astro_15m_dict, astro_future_hilo_dict = astro.get_astro_tides(
        timeline, max_observed_dt
    )
    past_surge_dict = sg.calculate_past_storm_surge(timeline, astro_15m_dict, obs_dict)
    future_surge_dict = sg.get_future_surge_data(
        timeline, max_observed_dt
    )  # {dt: surge_value}

    # Now we have all the data we need. Build the lists required by the graph plots, which must be the
    # same length as the timeline so the front end can graph them. They are sparse -- with None for any missing data.
    hist_tides_plot = list(map(lambda dt: obs_dict.get(dt, None), timeline))
    hist_hilo_dts = obs_hilo_dict.keys()
    hist_hilo_vals = obs_hilo_dict.values()
    wind_speed_plot, wind_gust_plot, wind_dir_plot, wind_dir_hover = build_wind_plots(
        timeline, wind_dict
    )
    astro_tides_plot, astro_hilo_dts, astro_hilo_vals = build_astro_data(
        timeline, astro_15m_dict, astro_future_hilo_dict
    )
    past_surge_plot = list(map(lambda dt: past_surge_dict.get(dt, None), timeline))
    future_surge_plot, future_storm_tide_plot = build_future_surge_plots(
        timeline, future_surge_dict, astro_15m_dict, astro_future_hilo_dict
    )
    highest_annual_predictions = build_annual_astro_high_plot(timeline)

    # If the timeline includes any future times, we want to replace the times of the high/low tides with the
    # actual times of those highs and lows, rather than the nearest 15 minute interval. This gives the users
    # the most accurate information possible.
    best_timeline = [
        astro_future_hilo_dict[dt]["real_dt"] if dt in astro_future_hilo_dict else dt
        for dt in timeline
    ]
    past_tl_index, future_tl_index = util.get_timeline_boundaries(best_timeline)
    start_date_str = timeline[0].strftime("%m/%d/%Y")
    end_date_str = timeline[-2].strftime("%m/%d/%Y")
    return {
        "timeline": best_timeline,
        "hist_tides": hist_tides_plot,
        "hist_hilo_dts": hist_hilo_dts,
        "hist_hilo_vals": hist_hilo_vals,
        "astro_tides": astro_tides_plot,
        "astro_hilo_dts": astro_hilo_dts,
        "astro_hilo_vals": astro_hilo_vals,
        "wind_speeds": wind_speed_plot,
        "wind_gusts": wind_gust_plot,
        "wind_dir": wind_dir_plot,
        "wind_dir_hover": wind_dir_hover,
        "record_tide": cfg.get_record_tide(),
        "past_surge": past_surge_plot,
        "future_surge": future_surge_plot,
        "future_tide": future_storm_tide_plot,
        "record_tide_title": f"{record_tide_title} ({cfg.get_record_tide():.2f})",
        "mean_high_water": cfg.get_mean_high_water(),
        "highest_annual_predictions": highest_annual_predictions,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "num_days": (end_date - start_date).days + 1,
        "past_tl_index": past_tl_index,
        "future_tl_index": future_tl_index,
    }


def build_future_surge_plots(
    timeline, future_surge_dict, reg_preds_dict, future_hilo_dict
) -> tuple[list, list]:
    """
    Build 2 plots for future surge data:
    1. Future surve values
    2. Future storm tide values, which is the sum of the future surge and the predicted tide.
    Params:
        timeline: list of datetimes
        future_surge_dict: {dt: surge_value}
        reg_preds_dict: {dt: value}
        future_hilo_dict: {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}}
    """
    future_surge_plot = []
    future_storm_tide_plot = []
    if len(future_surge_dict) == 0:
        # No future surge data, so return None for both plots.
        return None, None
    first_dt = min(future_surge_dict)
    last_surge_dt = None
    last_surge_val = None
    for dt in timeline:
        if dt >= first_dt:
            future_pred = (
                future_hilo_dict.get(dt)["value"]
                if dt in future_hilo_dict
                else reg_preds_dict.get(dt, None)
            )
            if future_pred is None:
                logger.error(f"Missing future prediction for {dt}")
                future_surge_plot.append(None)
                future_storm_tide_plot.append(None)
            else:
                surge_val = future_surge_dict.get(dt, None)
                if surge_val is not None:
                    last_surge_dt = dt
                    last_surge_val = surge_val
                elif last_surge_dt is not None and dt - last_surge_dt < timedelta(
                    hours=1
                ):
                    surge_val = last_surge_val
                if surge_val is not None:
                    future_surge_plot.append(surge_val)
                    future_storm_tide_plot.append(round(surge_val + future_pred, 2))
                else:
                    future_surge_plot.append(None)
                    future_storm_tide_plot.append(None)
        else:
            future_surge_plot.append(None)
            future_storm_tide_plot.append(None)

    return future_surge_plot, future_storm_tide_plot


def build_astro_data(
    timeline, reg_preds_dict, future_hilo_dict
) -> tuple[list, list, list]:
    """
    Builds lists for the astronomical tide data.
    1. Matching plot data for the astronomical tide values, including Nones where data is missing (unlikely).
    2. List of just the datetimes of the high/low tides, for convenience of the app
    3. List of the matching high/low tide values, for convenience of the app
    Params:
        timeline: list of datetimes
        reg_preds_dict: {dt: value}
        future_hilo_dict: {dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}}
    """
    astro_tides_plot = []
    astro_hilo_dts = []
    astro_hilo_vals = []

    for dt in timeline:
        if dt in future_hilo_dict:
            item = future_hilo_dict[dt]
            astro_tides_plot.append(item["value"])
            astro_hilo_dts.append(item["real_dt"])
            astro_hilo_vals.append(item["type"])
        else:
            astro_tides_plot.append(reg_preds_dict.get(dt, None))

    return astro_tides_plot, astro_hilo_dts, astro_hilo_vals


def build_wind_plots(timeline, wind_dict) -> tuple[list, list, list, list]:
    """
    Convert wind data dict to sparse plot lists.
    1. Wind speed
    2. Wind gust
    3. Wind direction
    4. Wind direction string
    Params:
        timeline: list of datetimes for the graph
        wind_dict: {dt: {speed, gust, dir, dir_str}}
    """
    # {dt: {speed, gust, dir, dir_str}}
    wind_speed_plot = []
    wind_gust_plot = []
    wind_dir_plot = []
    wind_dir_hover = []
    for dt in timeline:
        if dt in wind_dict:
            wind_data = wind_dict[dt]
            wind_speed_plot.append(wind_data["speed"])
            wind_gust_plot.append(wind_data["gust"])
            wind_dir_plot.append(wind_data["dir"])
            wind_dir_hover.append(wind_data["dir_str"])
        else:
            wind_speed_plot.append(None)
            wind_gust_plot.append(None)
            wind_dir_plot.append(None)
            wind_dir_hover.append(None)

    return wind_speed_plot, wind_gust_plot, wind_dir_plot, wind_dir_hover


def build_annual_astro_high_plot(timeline) -> list:
    """
    Build plot list for the highest annual predicted tide plot, using the configured settings.
    If it crosses a year boundary, we'll switch to that value at the appropriate time.
    Since these will be shown as static, connected points, and not included in the hover text, we only need
    to supply the initial and final values, with None's in between.
    TODO: Just supply the values and offsets, and let the front end fill in the rest.
    """
    time_count = len(timeline)
    high1 = cfg.get_astro_high_tide(timeline[0].year)

    # To determine the year of the last data point, we will ignore the extra midnight time added to the timeline,
    # so it's timeline[-2] not timeline[-1]
    if timeline[0].year == timeline[-2].year:
        highs = [high1] + [None] * (time_count - 2) + [high1]
    else:
        # We're crossing a year boundary. Get the 2nd year's high.
        year2 = timeline[-1].year
        high2 = cfg.get_astro_high_tide(year2)
        # Figure out where in the index year 2 starts
        for offset, dt in enumerate(timeline):
            if dt.year == year2:
                break
        highs = (
            [high1]
            + [None] * (offset - 2)
            + [high1, high2]
            + [None] * (time_count - offset - 2)
            + [high2]
        )

    if len(highs) != time_count:
        raise APIException()
    return highs


def validate_dates(start, end):
    earliest_date = date(cfg.get_supported_years()[0], 1, 1)
    latest_date = date(cfg.get_supported_years()[-1], 12, 31)
    if (
        start > latest_date
        or start < earliest_date
        or end > latest_date
        or end < earliest_date
    ):
        logger.error(
            f"Invalidate range: {start} - {end} is not between {earliest_date} - {latest_date}"
        )
        # This will return a code 400
        raise ValidationError(
            detail="Invalid date range"
        )  # Override the default 'Invalid input'
    if end < start:
        logger.error(f"end_date {end} cannot be earlier than start_date {start}")
        raise ValidationError(detail="end date less than start date")
