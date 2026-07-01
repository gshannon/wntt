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
    each callback would return None, so we can just return None for both lists.

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

    def get_hilo_label(dt: datetime):
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            # If it's a PredictedHighOrLow, that means there wasn't enough observed data to determine
            # the observed high or low, so don't label it.
            if isinstance(event, ObservedHighOrLow):
                return "(HIGH)" if event.hilo == Hilo.HIGH else "(LOW)"
        return None

    def get_tide(dt: datetime):
        # If this is a Hilo graph, we don't show tides that are not a high or low.
        if isinstance(timeline, HiloTimeline):
            return hilo_event_dict[dt].value if dt in hilo_event_dict else None
        return water_dict[dt][cdmo.Param.Tide.label] if dt in water_dict else None

    hist_tides_plot = timeline.build_plot(get_tide)
    hist_tides_labels = timeline.build_plot(get_hilo_label)
    return hist_tides_plot, hist_tides_labels


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

    found = False

    # If not in hilo mode, for readability, thin out the data points, as it gets pretty dense and hard to read.
    minutes = [0, 15, 30, 45]  # show all
    if not isinstance(timeline, HiloTimeline):
        days = (timeline.end_dt.date() - timeline.start_dt.date()).days
        if days == 2:
            minutes = [0, 30]  # show 2 per hour
        elif days > 2:
            minutes = [0]  # only show 1 point per hour

    def check_item(dt, key):
        nonlocal found
        # If this is a Hilo graph, we don't only show wind high or low.
        if isinstance(timeline, HiloTimeline) and dt not in hilo_event_dict:
            return None

        if dt.minute in minutes and dt in wind_dict:
            if key not in wind_dict[dt]:
                raise util.InternalError(f"Missing {key} in wind data for {dt}")
            found = True
            return wind_dict[dt].get(key)
        else:
            return None

    def check_speed(dt):
        return check_item(dt, cdmo.Param.WindSpeed.label)

    def check_gust(dt):
        return check_item(dt, cdmo.Param.WindGust.label)

    def check_dir(dt):
        return check_item(dt, cdmo.Param.WindDir.label)

    wind_speed_plot = timeline.build_plot(check_speed)
    wind_gust_plot = timeline.build_plot(check_gust)
    wind_dir_plot = timeline.build_plot(check_dir)

    if not found:
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
        reg_preds_dict (dict): {dt: value} for 15-min predictions over entire timeline
        hilo_event_dict (dict): {dt: HighOrLow} High/Low predictions after last observed.

    Returns:
        - Matching plot data for the astronomical tide values, including Nones where data is missing (unlikely).
        - Corresponding "(HIGH)" or "(LOW)" labels where applicable
    """

    # For value, we'll almost always use the 15-min prediction. In the rare case we have a PredictedHighOrLow
    # for the timeline dt, that indicates we didn't have enough observed data to build an ObservedHighOrOLow,
    # and we'll be displaying this predicted value which came from the HILO dataset, not the 15-min predictions.
    # That's obviously a more accurate number than the 15-min predictions.
    def get_value(dt):
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            # ignore it if it's an ObservedHighOrLow
            if isinstance(event, PredictedHighOrLow):
                return event.value
            return reg_preds_dict.get(dt, None)

        # It wasn't a high/low, so if this is a Hilo graph, it gets a None.
        return (
            reg_preds_dict.get(dt, None)
            if not isinstance(timeline, HiloTimeline)
            else None
        )

    # We almost never label past predicted highs/lows because we label the observed high/lows instead. But
    # if there's a PredictedHighOrLow in the hilo events, that indicates we didn't have enough observed data
    # to determine a high/low. Therefore it's better to label the prediction, else there would be no high/low labeled.
    def get_label(dt):
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            if isinstance(event, PredictedHighOrLow):
                return ("(HIGH)" if event.hilo == Hilo.HIGH else "(LOW)",)
        return None

    astro_tides_plot = timeline.build_plot(get_value)
    astro_labels_plot = timeline.build_plot(get_label)

    return astro_tides_plot, astro_labels_plot


def build_past_surge_plot(
    timeline: GraphTimeline, past_surge_dict: dict, hilo_event_dict: dict
):

    if timeline.is_all_future():
        return None

    isHilo = isinstance(timeline, HiloTimeline)

    def check(dt):
        nonlocal isHilo
        if isHilo and dt not in hilo_event_dict:
            return None
        return past_surge_dict.get(dt, None)

    return timeline.build_plot(check)


def build_past_surge_check_plots(
    timeline: GraphTimeline, pred_dict, astro_preds15_dict
) -> tuple[list, list]:
    if len(pred_dict) == 0:
        return None, None

    found = False

    def get_pred(dt: datetime):
        nonlocal found
        found = found or dt in pred_dict
        return pred_dict.get(dt, None)

    def get_total_pred(dt: datetime):
        nonlocal found
        # lookup_dt = dt if dt.minute == 0 else dt.replace(minute=0)
        if dt in pred_dict and dt in astro_preds15_dict:
            found = True
            return pred_dict[dt] + astro_preds15_dict[dt]
        return None

    surge_plot = timeline.build_plot(lambda dt: get_pred(dt))
    if found:
        total_plot = timeline.build_plot(lambda dt: get_total_pred(dt))
        return surge_plot, total_plot
    else:
        return None, None


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
        # No future surge data, so return None for both plots.
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

    def handle_surge_pred(dt):
        surge_val, _ = get_surge_and_hilo_prediction(dt)
        return surge_val

    def handle_storm_surge(dt):
        surge_val, hilo_pred = get_surge_and_hilo_prediction(dt)
        return (
            round(surge_val + hilo_pred, 2)
            if surge_val is not None and hilo_pred is not None
            else None
        )

    future_surge_plot = timeline.build_plot(handle_surge_pred)
    future_storm_tide_plot = timeline.build_plot(handle_storm_surge)

    if len(future_surge_plot) != len(future_storm_tide_plot):
        msg = f"{len(future_surge_plot)} != {len(future_storm_tide_plot)}"
        logger.error(msg)
        raise util.InternalError(msg)

    return future_surge_plot, future_storm_tide_plot


def build_wind_forecast_plots(
    timeline: GraphTimeline, forecast_dict: dict
) -> tuple[list, list]:
    """
    Build data for 2 graph plots for wind forecast -- speed and direction (degrees)

    Args:
        timeline (GraphTimeline): the timeline
        forecast_dict (dict): forecast data.

    Returns:
        - forecast_wind_speed_plot:
        - Corresponding wind direction plost (0-360), to drive marker angle)
    """
    if len(forecast_dict) == 0:
        return None, None

    found = False

    def get_value(dt):
        nonlocal found
        if dt in forecast_dict:
            found = True
            return forecast_dict[dt].get("mph")
        return None

    def get_dir_degrees(dt):
        if dt in forecast_dict:
            return forecast_dict[dt].get("dir")
        return None

    forecast_speed_plot = timeline.build_plot(get_value)
    forecast_wind_dir_plot = timeline.build_plot(get_dir_degrees)

    if not found:
        return None

    return forecast_speed_plot, forecast_wind_dir_plot
