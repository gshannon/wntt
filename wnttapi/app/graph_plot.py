import logging
from datetime import datetime, timedelta

from app import util
from app.datasource import cdmo
from app.hilo import Hilo, ObservedHighOrLow, PredictedHighOrLow
from app.timeline import GraphTimeline, HiloTimeline

logger = logging.getLogger(__name__)


def build_hist_tide_plot(
    timeline: GraphTimeline, water_dict: dict, hilo_event_dict: dict
) -> tuple[list, list]:
    """Build historical tide plot and high or low tide labels. For timelines entirely in the future,
    each callback would return None, so we can just return None for both lists. Never returns empty lists.

    Args:
        timeline (GraphTimeline): the timeline
        water_dict: dense dict of observed tide readings {datetime: {"level": val, "temp": val"}}
        hilo_event_dict: dense dict of all high/low tides, {timeline_dt: HighOrLow}


    Returns:
        tuple[list, list]:
        - hist_tides_plot: list of historical tide heights in MLLW feet, or None if no data
        - hist_tides_labels: corresponding "(HIGH)" or "(LOW)" labels, when applicable
    """

    if timeline.is_all_future():
        return None, None

    def get_elements(dt: datetime):
        # If this is a Hilo graph, we don't show tides that are not a high or low observed tide.
        tide = label = None
        if isinstance(timeline, HiloTimeline):
            if dt in hilo_event_dict and isinstance(
                hilo_event_dict[dt], ObservedHighOrLow
            ):
                hiOrLow = hilo_event_dict[dt]
                tide = hiOrLow.value
                label = "(HIGH)" if hiOrLow.hilo == Hilo.HIGH else "(LOW)"
        elif dt in water_dict:
            tide = water_dict[dt][cdmo.Param.Tide.label]
        return tide, label

    tides, labels = timeline.build_plots(get_elements)
    if all(x is None for x in tides):
        return None, None
    return tides, labels


def build_wind_plots(
    timeline: GraphTimeline, wind_dict: dict, hilo_event_dict: dict
) -> tuple[list, list, list]:
    """Convert the recorded wind data to 4 plots for Plotly scatter plots.

    Args:
        timeline (GraphTimeline): timeline
        wind_dict (dict): {dt: {'speed': x, 'gust': x, 'dir_deg': x}}

    Returns:
        - Wind speed plot
        - Wind gust plot
        - Corresponding wind direction (0 - 360) to drive marker angle
    """

    if len(wind_dict) == 0:
        # There are no wind predictions, return None for all lists.
        return None, None, None

    # If not in hilo mode, for readability, thin out the data points, as it gets pretty dense and hard to read.
    minutes = [0, 15, 30, 45]  # show all
    if not isinstance(timeline, HiloTimeline):
        days = (timeline.end_dt.date() - timeline.start_dt.date()).days
        if days == 2:
            minutes = [0, 30]  # show 2 per hour
        elif days > 2:
            minutes = [0]  # only show 1 point per hour

    def get_elements(dt: datetime):
        if not isinstance(timeline, HiloTimeline) or dt in hilo_event_dict:
            if dt.minute in minutes and dt in wind_dict:
                return (
                    wind_dict[dt].get(cdmo.Param.WindSpeed.label),
                    wind_dict[dt].get(cdmo.Param.WindGust.label),
                    wind_dict[dt].get(cdmo.Param.WindDir.label),
                )
        return None, None, None

    wind_speed_plot, wind_gust_plot, wind_dir_plot = timeline.build_plots(get_elements)

    if all(x is None for x in wind_speed_plot):
        return None, None, None

    return wind_speed_plot, wind_gust_plot, wind_dir_plot


def build_astro_plot(
    timeline: GraphTimeline,
    reg_preds_dict: dict,
    hilo_event_dict: dict,
) -> tuple[list, list]:
    """
    Builds plots for the astronomical tide data. We essentially merge the regular 15-min predictions and the
    hilo data, preferring the hilo value if present, which is more accurate.

    Args:
        timeline (GraphTimeline): the time line
        reg_preds_dict (dict): {dt: value} 15-min predictions over entire timeline
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline

    Returns:
        (list of predicted tide values/None, list of high/low labels/None) to match the timeline.
    """

    def get_elements(dt: datetime):

        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            # If it's a PredictedHighOrLow, we use it no matter if we're in past or future.   If it's in the past,
            # that means there wasn't a deterministic observed high/low, so this is better than nothing.
            if isinstance(event, PredictedHighOrLow):
                return event.value, ("(HIGH)" if event.hilo == Hilo.HIGH else "(LOW)",)

        if isinstance(timeline, HiloTimeline) and dt not in hilo_event_dict:
            # If this is a Hilo graph, we don't show tides that are not a high or low tide.
            return None, None

        return reg_preds_dict.get(dt, None), None

    tides, labels = timeline.build_plots(get_elements)
    if all(x is None for x in tides):
        return None, None
    return tides, labels


def build_past_surge_plot(
    timeline: GraphTimeline, past_surge_dict: dict, hilo_event_dict: dict
):
    """ 
    Build a plot for recorded storm surge. 

    Args:
        timeline (GraphTimeline): the time line
        past_surge_dict (dict): {dt: value} recorded storm surge values
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline

    Returns:
        list of recorded storm surge values to match the timeline.  Returns None if all values are None.
    """

    if timeline.is_all_future():
        return None

    isHilo = isinstance(timeline, HiloTimeline)

    def get_element(dt):
        if isHilo and dt not in hilo_event_dict:
            return None
        return past_surge_dict.get(dt, None)

    plot = timeline.build_plots(get_element) 
    return plot if all(x is None for x in plot) else None


def build_future_surge_plots(
    timeline: GraphTimeline,
    future_surges_dict: dict,
    future_surge_calc_bias: float,
    reg_preds_dict: dict,
    astro_hilo_dict: dict,
) -> tuple[list, list]:
    """
    Build 2 plots for future surge data. For each timeline datetime, we'll use the most accurate prediction we have
    (future_hilo_dict if present), then add that to the surge value to produce predicted storm tide.

    Args:
        timeline: list of datetimes
        future_surges_dict: what we read from the surge file {dt: surge_value}
        future_surge_calc_bias: calculated bias to be applied the surge values, or None.
            This will only be set for reserves like Wells, where there is no BIAS data in the files.
            Bias values provided in the file are already applied to these surge values.
        reg_preds_dict: regular tide & currents tide predictions for the timeline {dt: value}
        future_hilo_dict: predicted highs and lows {timeline_dt: HighLowEvent}
    """
    if future_surges_dict is None or len(future_surges_dict) == 0:
        return None, None

    # If a dt doesn't have a surge value, we can use one up to 45 minutes older, since surge values
    # are on the hour.
    def find_nearby_surge(dt):
        surge = None
        try_dt = dt
        while True:
            surge = future_surges_dict.get(try_dt, None)
            if surge is not None:
                # Add the calculated bias if any.
                surge += future_surge_calc_bias or 0
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
            astro_hilo_dict.get(dt).value
            if dt in astro_hilo_dict
            else reg_preds_dict.get(dt, None)
        )
        if surge_val is not None and hilo_pred is None:
            msg = f"Missing future prediction for {dt}"
            logger.error(msg)
            raise util.InternalError(msg)
        return surge_val, hilo_pred

    def get_elements(dt):
        if timeline.is_past(dt) or (
            isinstance(timeline, HiloTimeline) and dt not in astro_hilo_dict
        ):
            return None, None  # This dt is in the past, or not in the hilo timeline
        surge_val, hilo_pred = get_surge_and_hilo_prediction(dt)
        if surge_val and hilo_pred:
            return round(surge_val, 2), round(surge_val + hilo_pred, 2)
        return None, None

    future_surge_plot, future_storm_tide_plot = timeline.build_plots(get_elements)

    if all(x is None for x in future_surge_plot):
        return None, None

    return future_surge_plot, future_storm_tide_plot


def build_wind_forecast_plots(
    timeline: GraphTimeline, forecast_dict: dict, hilo_event_dict: dict
) -> tuple[list, list]:
    """
    Build data for 2 graph plots for wind forecast -- speed and direction (degrees)

    Args:
        timeline (GraphTimeline): the timeline
        forecast_dict (dict): forecast data.
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline

    Returns:
        - forecast_wind_speed_plot:
        - Corresponding wind direction plost (0-360), to drive marker angle)
    """
    if len(forecast_dict) == 0:
        return None, None

    def get_element(dt):
        if isinstance(timeline, HiloTimeline) and dt not in hilo_event_dict:
            return None, None
        if dt in forecast_dict:
            return (
                forecast_dict[dt].get("mph"),
                forecast_dict[dt].get("dir"),
            )
        return None, None

    forecast_speed_plot, forecast_wind_dir_plot = timeline.build_plots(get_element)

    if all(x is None for x in forecast_speed_plot):
        return None, None

    return forecast_speed_plot, forecast_wind_dir_plot
