import logging
from datetime import date, datetime, timedelta

from app import util
from app.datasource import astrotide as astro
from app.datasource import cdmo, moon
from app.datasource import surge as sg
from app.datasource.apiutil import APICall, run_parallel
from app.timeline import GraphTimeline, HiloTimeline
from rest_framework.exceptions import ValidationError

from . import station as stn

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


def get_graph_data(
    start_date: date, end_date: date, hilo_mode: bool, station: stn.Station
):
    """Generate plot data.

    Args:
        start_date (date): First day of data
        end_date (date): Last day of data (may be same as first). 00:00 of following day will be added automatically.
        hilo_mode (bool): If true, data will include only high and low tide data points.
        station (Station): Station for which to get data

    Returns:
        dict: All data required for graph, suitable for json
    """

    validate_dates(start_date, end_date)

    if hilo_mode:
        timeline = HiloTimeline(start_date, end_date, station.time_zone)
    else:
        timeline = GraphTimeline(start_date, end_date, station.time_zone)

    # Get moon/sun tide data
    syzygy_data = moon.get_syzygy_data(timeline)
    # Phase 1: Retrieve all data from external sources. All these dicts are dense -- they
    # only have keys for actual data, not None, and are keyed by the datetime from the timeline.

    # Start with the observed tide data and wind data, which may be useful in gathering other data.
    obs_dict, wind_dict = get_cdmo_data(timeline, station)

    # Determine observed highs and lows.
    obs_hilo_dict = cdmo.find_hilos(timeline, obs_dict)

    # Get 15-minute interval astronomical tide predictions for the entire timeline.
    astro_preds15_dict = astro.get_15m_astro_tides(station, timeline)

    # For annotating High and Low tides, observed data takes precedence over predicted, so we
    # don't bother pulling predictions for the part of the timeline in the past, apart from the data lag
    # period -- between the last observed data and the present.
    last_recorded_dt = max(obs_dict) if len(obs_dict) > 0 else None
    astro_later_hilo_dict = astro.get_hilo_astro_tides(
        station, timeline, last_recorded_dt
    )

    if hilo_mode:
        # The HiloTimeline needs to keep track of these for later processing.
        timeline.register_hilo_times(
            list(obs_hilo_dict.keys()) + list(astro_later_hilo_dict.keys())
        )

    past_surge_dict = sg.calculate_past_storm_surge(astro_preds15_dict, obs_dict)
    future_surge_dict = sg.get_future_surge_data(
        timeline, station.noaa_station_id, last_recorded_dt
    )

    # Phase 2. Now we have all the data we need, in dense dictionaries. Build the lists required
    # by the graph plots, which must be the same length as the timeline so the front end can graph them.
    # They are sparse rather than dense -- they have None for any missing data.
    hist_tides_plot, hist_hilo_labels = build_hist_tide_plot(
        timeline, obs_dict, obs_hilo_dict
    )

    wind_speed_plot, wind_gust_plot, wind_dir_plot, wind_dir_hover = build_wind_plots(
        timeline, wind_dict
    )
    astro_tides_plot, astro_hilo_labels = build_astro_plot(
        timeline, astro_preds15_dict, astro_later_hilo_dict
    )

    past_surge_plot = (
        timeline.build_plot(lambda dt: past_surge_dict.get(dt, None))
        if not timeline.is_all_future()
        else None
    )
    future_surge_plot, future_storm_tide_plot = build_future_surge_plots(
        timeline, future_surge_dict, astro_preds15_dict, astro_later_hilo_dict
    )

    # If we've prepared any predicted high or low tides times, which have actual times rather than the nearest
    # 15-min time, we want to replace those timeline times with the real times, so they show accurately on the graph.
    # Since the timeline is just a list of datetimes and the plots are a list of data values or None, all we have to
    # do is replace those values in the timeline, and then return the timeline with the plots.
    if len(astro_later_hilo_dict) > 0:
        final_timeline = timeline.get_final_times(
            {key: val["real_dt"] for key, val in astro_later_hilo_dict.items()}
        )
    else:
        final_timeline = timeline.get_final_times({})
    past_tl_index, future_tl_index = util.get_timeline_boundaries(final_timeline)
    start_date_str = timeline.start_date.strftime("%m/%d/%Y")
    end_date_str = timeline.end_date.strftime("%m/%d/%Y")
    return {
        "timeline": final_timeline,
        "syzygy": syzygy_data,
        "hist_tides": hist_tides_plot,
        "hist_hilo_labels": hist_hilo_labels,
        "astro_tides": astro_tides_plot,
        "astro_hilo_labels": astro_hilo_labels,
        "wind_speeds": wind_speed_plot,
        "wind_gusts": wind_gust_plot,
        "wind_dir": wind_dir_plot,
        "wind_dir_hover": wind_dir_hover,
        "past_surge": past_surge_plot,
        "future_surge": future_surge_plot,
        "future_tide": future_storm_tide_plot,
        "highest_annual_prediction": stn.get_astro_high_tide_mllw(
            station, start_date.year
        ),
        "start_date": start_date_str,
        "end_date": end_date_str,
        "num_days": (end_date - start_date).days + 1,
        "past_tl_index": past_tl_index,
        "future_tl_index": future_tl_index,
    }


def get_cdmo_data(timeline: GraphTimeline, station: stn.Station) -> tuple[dict, dict]:
    """Retrieve all cdmo historical data needed for the graph. We do these calls in parallel to save time.

    Args:
        timeline (GraphTimeline)
        station (Station)

    Raises:
        APIException: if a call fails

    Returns:
        tuple[dict, dict]: tide_dict, wind_dict.  Both will be empty if timeline is all in future.
    """
    if timeline.is_all_future():
        return {}, {}

    cdmo_calls = [
        APICall(
            "tide",
            cdmo.get_recorded_tides,
            station,
            timeline,
        ),
        APICall(
            "wind",
            cdmo.get_recorded_wind_data,
            station,
            timeline,
        ),
    ]

    run_parallel(cdmo_calls)

    return cdmo_calls[0].data, cdmo_calls[1].data


def build_hist_tide_plot(
    timeline: GraphTimeline, obs_dict: dict, obs_hilo_dict: dict
) -> tuple[list, list]:
    """Build historical tide plot and high or low tide labels. For timelines entirely in the future,
    each callback would return None, so we can just return None for both lists.

    Args:
        timeline (GraphTimeline): the timeline
        obs_dict (dict): observed tides {dt: height MLLW feet}
        obs_hilo_dict (dict): {dt: 'H' or 'L'} for high or low tide, keyed by datetime

    Returns:
        tuple[list, list]:
        - hist_tides_plot: list of historical tide heights in MLLW feet, or None if no data
        - hist_hilo_labels: list of corresponding high or low tide labels or '' for each datetime in the timeline
    """

    if timeline.is_all_future():
        return None, None

    def get_hilo_label(dt: datetime):
        if dt in obs_hilo_dict:
            return "(HIGH)" if obs_hilo_dict[dt] == "H" else "(LOW)"
        return ""

    hist_tides_plot = timeline.build_plot(lambda dt: obs_dict.get(dt, None))
    hist_hilo_labels = timeline.build_plot(get_hilo_label)
    return hist_tides_plot, hist_hilo_labels


def build_future_surge_plots(
    timeline: GraphTimeline,
    future_surge_dict: dict,
    reg_preds_dict: dict,
    astro_hilo_dict: dict,
) -> tuple[list, list]:
    """
    Build 2 plots for future surge data. For each timeline datetime, we'll use the most accurate prediction we have
    (future_hilo_dict if present), then add that to the surge value to produce predicted storm tide.

    Args:
        timeline: list of datetimes
        future_surge_dict: {dt: surge_value}
        reg_preds_dict: {dt: value}
        future_hilo_dict: {timeline_dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}}
    """
    if len(future_surge_dict) == 0:
        # No future surge data, so return None for both plots.
        return None, None

    # If a dt doesn't have a surge value, we can use one up to 45 minutes older, since surge values
    # are on the hour.
    def find_nearby_surge(dt):
        surge = None
        try_dt = dt
        while True:
            surge = future_surge_dict.get(try_dt, None)
            if surge is not None:
                break
            try_dt -= timedelta(minutes=15)
            if try_dt < dt - timedelta(minutes=45):
                break
        return surge

    def get_surge_and_hilo_prediction(dt):
        surge_val = find_nearby_surge(dt)
        if surge_val is None:
            return None, None
        hilo_pred = (
            astro_hilo_dict.get(dt)["value"]
            if dt in astro_hilo_dict
            else reg_preds_dict.get(dt, None)
        )
        if surge_val is not None and hilo_pred is None:
            logger.error(f"Missing future prediction for {dt}")
            return None, None
        return surge_val, hilo_pred

    def handle_surge_pred(dt):
        surge_val, _ = get_surge_and_hilo_prediction(dt)
        return surge_val

    def handle_storm_surge(dt):
        surge_val, hilo_pred = get_surge_and_hilo_prediction(dt)
        return (
            round(surge_val + hilo_pred, 2)
            if surge_val is not None and hilo_pred
            else None
        )

    future_surge_plot = timeline.build_plot(handle_surge_pred)
    future_storm_tide_plot = timeline.build_plot(handle_storm_surge)

    if len(future_surge_plot) != len(future_storm_tide_plot):
        logger.error(f"{len(future_surge_plot)} != {len(future_storm_tide_plot)}")
        raise ValidationError()

    return future_surge_plot, future_storm_tide_plot


def build_astro_plot(
    timeline: GraphTimeline, reg_preds_dict: dict, later_hilo_dict: dict
) -> tuple[list, list]:
    """
    Builds plots for the astronomical tide data. We essentially merge the regular 15-min predictions and the
    hilo data, preferring the hilo value if present, which is more accurate.

    Args:
        timeline (GraphTimeline): the time line
        reg_preds_dict (dict): {dt: value} for 15-min predictions over entire timeline
        later_hilo_dict (dict): {dt: {'real_dt': dt, 'value': val, 'type': 'H' or 'L'}} High/Low predictions after last observed.

    Returns:
        tuple[list, list, list]:
        - Matching plot data for the astronomical tide values, including Nones where data is missing (unlikely).
        - List of just the datetimes of the high/low tides, for convenience of the app
        - List of the matching high/low tide labels ('H' or 'L'), for convenience of the app
    """

    def check_later(dt, key):
        if dt in later_hilo_dict:
            return later_hilo_dict[dt].get(key, None)
        else:
            return None

    def get_value(dt):
        # For value, prefer the later_hilo_dict value if present, else use the regular predictions.
        val = check_later(dt, "value")
        return val or reg_preds_dict.get(dt, None)

    def get_type(dt):
        type = check_later(dt, "type")
        if type is None:
            return ""
        return "(HIGH)" if type == "H" else "(LOW)"

    astro_tides_plot = timeline.build_plot(get_value)
    astro_hilo_labels = timeline.build_plot(get_type)

    return astro_tides_plot, astro_hilo_labels


def build_wind_plots(
    timeline: GraphTimeline, wind_dict: dict
) -> tuple[list, list, list, list]:
    """Convert the recorded wind data to 4 plots for Plotly scatter plots.

    Args:
        timeline (GraphTimeline): timeline
        wind_dict (dict):     )  dict of the form {dt: {speed, gust, dir, dir_str}}

    Returns:
        1. Wind speed
        2. Wind gust
        3. Wind direction (0-360, to drive marker angle)
        4. Wind direction string (for hover text display)
    """
    if len(wind_dict) == 0:
        # There are no wind predictions, return None for all lists.
        return None, None, None, None

    # If not in hilo mode, for readability, thin out the data points, as it gets pretty dense and hard to read.
    minutes = [0, 15, 30, 45]  # show all
    if not isinstance(timeline, HiloTimeline):
        days = (timeline.end_dt.date() - timeline.start_dt.date()).days
        if days > 5:
            minutes = [0]  # only show 1 point per hour
        elif days > 2:
            minutes = [0, 30]  # show 2 per hour

    def check_item(dt, key):
        if dt.minute in minutes and dt in wind_dict:
            return wind_dict[dt].get(key, None)
        else:
            return None

    def check_speed(dt):
        return check_item(dt, "speed")

    def check_gust(dt):
        return check_item(dt, "gust")

    def check_dir(dt):
        return check_item(dt, "dir")

    def check_dir_str(dt):
        return check_item(dt, "dir_str")

    wind_speed_plot = timeline.build_plot(check_speed)
    wind_gust_plot = timeline.build_plot(check_gust)
    wind_dir_plot = timeline.build_plot(check_dir)
    wind_dir_hover = timeline.build_plot(check_dir_str)

    return wind_speed_plot, wind_gust_plot, wind_dir_plot, wind_dir_hover


def validate_dates(start: date, end: date):
    """Verify the requested start and end dates are legal.

    Args:
        start (date): First full date to display
        end (date): Last full day to display

    Raises:
        ValidationError: If date range is too big, or end < start.
    """
    earliest_date = date(stn.get_supported_years()[0], 1, 1)
    latest_date = date(stn.get_supported_years()[-1], 12, 31)
    if (
        start > latest_date
        or start < earliest_date
        or end > latest_date
        or end < earliest_date
    ):
        logger.error(
            f"Invalid range: {start} - {end} is not between {earliest_date} - {latest_date}"
        )
        # This will return a code 400
        raise ValidationError(
            detail="Invalid date range"
        )  # Override the default 'Invalid input'
    if end < start:
        logger.error(f"end_date {end} cannot be earlier than start_date {start}")
        raise ValidationError(detail="end date less than start date")
