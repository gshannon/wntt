import logging
from datetime import datetime, timedelta

from app import util
from app.datasource import cdmo
from app.hilo import Hilo, ObservedHighOrLow, PredictedHighOrLow
from app.timeline import GraphTimeline, HiloTimeline

logger = logging.getLogger(__name__)


def build_observed_tide_plot(
    timeline: GraphTimeline, water_dict: dict, hilo_event_dict: dict
) -> tuple[list, list]:
    """Build lists for observed tide and high or low tide labels that match the timeline length. If there's
    no observed tide data for the timeline, returns None for both lists.

    Args:
        timeline (GraphTimeline): the timeline
        water_dict: dense dict of observed tide readings {datetime: {"level": val, "temp": val"}}
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline,
            used to assign high/low labels to the tide plot.

    Returns:
        tuple[list, list].
        - hist_tides_plot: tide heights in MLLW feet, or None if no data;
        - hist_tides_labels: corresponding "(HIGH)" or "(LOW)" labels, when applicable, else None
    """

    if timeline.is_all_future():
        return None, None

    def getObservedHiloLabel(dt: datetime):
        if dt in hilo_event_dict and isinstance(hilo_event_dict[dt], ObservedHighOrLow):
            hiOrLow = hilo_event_dict[dt]
            return "(HIGH)" if hiOrLow.hilo == Hilo.HIGH else "(LOW)"
        return None

    def callback(dt: datetime):
        tide = None
        label = getObservedHiloLabel(dt)
        # If this is a Hilo graph, we don't show tides that are not a high or low observed tide.
        if isinstance(timeline, HiloTimeline):
            if label is not None:
                return water_dict[dt][cdmo.Param.Tide.label], label
        elif dt in water_dict:
            tide = water_dict[dt][cdmo.Param.Tide.label]
        return tide, label

    tides, labels = timeline.build_plots(callback)
    if all(x is None for x in tides):
        return None, None
    return tides, labels


def build_wind_plots(
    timeline: GraphTimeline, wind_dict: dict, hilo_event_dict: dict
) -> tuple[list, list, list]:
    """Build lists for wind data which correspond to the timeline.  Returns None for all lists if there
    is no wind data.

    Args:
        timeline (GraphTimeline): timeline
        wind_dict (dict): {dt: {'speed': x, 'gust': x, 'dir_deg': x}}. We rely on the fact that all 3 values
            are present for any given dt.
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline
            used to restrict returned data to only those times if we have a HiloTimeline.

    Returns: tuple[list, list, list].  All 3 lists have None in the same indexes -- no partial data is allowed.
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

    def callback(dt: datetime):
        if not isinstance(timeline, HiloTimeline) or dt in hilo_event_dict:
            if dt.minute in minutes and dt in wind_dict:
                return (
                    wind_dict[dt].get(cdmo.Param.WindSpeed.label),
                    wind_dict[dt].get(cdmo.Param.WindGust.label),
                    wind_dict[dt].get(cdmo.Param.WindDir.label),
                )
        return None, None, None

    wind_speed_plot, wind_gust_plot, wind_dir_plot = timeline.build_plots(callback)

    if all(x is None for x in wind_speed_plot):
        return None, None, None

    return wind_speed_plot, wind_gust_plot, wind_dir_plot


def build_astro_plot(
    timeline: GraphTimeline,
    reg_preds_dict: dict,
    hilo_event_dict: dict,
) -> tuple[list, list]:
    """
    Builds lists for the astronomical tide data. We essentially merge the regular 15-min predictions and the
    hilo-only data, preferring the hilo value if present, which is more accurate.

    Args:
        timeline (GraphTimeline): the time line
        reg_preds_dict (dict): {dt: value} 15-min predictions over entire timeline
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline

    Returns:
        (list of predicted tide values/None, list of high/low labels/None) to match the timeline.
    """

    def callback(dt: datetime):
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            # If it's a PredictedHighOrLow, we use it no matter if we're in past or future.   If it's in the past,
            # that means there wasn't a deterministic observed high/low, so this is better than nothing.
            if isinstance(event, PredictedHighOrLow):
                return event.value, ("(HIGH)" if event.hilo == Hilo.HIGH else "(LOW)",)

        if isinstance(timeline, HiloTimeline) and dt not in hilo_event_dict:
            # For HiloTimeline, we don't show tides that are not a high or low tide.
            return None, None

        return reg_preds_dict.get(dt, None), None

    tides, labels = timeline.build_plots(callback)
    if all(x is None for x in tides):
        return None, None
    return tides, labels


def build_past_surge_plot(
    timeline: GraphTimeline, past_surge_dict: dict, hilo_event_dict: dict
):
    """
    Build a list for recorded storm surge that corresponds to the timeline, with None for missing data.

    Args:
        timeline (GraphTimeline): the time line
        past_surge_dict (dict): {dt: value} recorded storm surge values
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline,
            used to restrict returned data to only those times if we have a HiloTimeline.

    Returns:
        list of recorded storm surge values to match the timeline.  Returns None if all values are None.
    """
    if timeline.is_all_future():
        return None

    isHilo = isinstance(timeline, HiloTimeline)

    def callback(dt):
        if isHilo and dt not in hilo_event_dict:
            return None
        return past_surge_dict.get(dt, None)

    plot = timeline.build_plots(callback)
    return None if all(x is None for x in plot) else plot


def build_future_surge_plots(
    timeline: GraphTimeline,
    future_surges_dict: dict,
    future_surge_calc_bias: float,
    reg_preds_dict: dict,
    astro_hilo_dict: dict,
) -> tuple[list, list]:
    """
    Build lists for predicted storm surge and predicted storm tide that correspond to the
    timeline, with None for missing data. For each timeline datetime, we'll use the astronomical
    tide prediction and add that to the surge value to produce predicted storm tide. Note
    that the surge data is hourly and the timeline is 15-min, so for each timeline time, we
    look for a surge value at that time, or up to 45 minutes earlier.

    Args:
        timeline: list of datetimes
        future_surges_dict: hourly surge predictions, in feet {dt: surge_value}
        future_surge_calc_bias: calculated bias to be applied the surge values, or None.
            This will only be set for reserves like Wells, where there is no BIAS data in the files.
            Bias values provided in the file are already applied to the surge values.
        reg_preds_dict: 15-minute astronomical tide predictions for the timeline {dt: value}

    Returns: tuple[list, list].  Both lists have None in the same indexes -- no partial data.
        - future_surge_plot: predicted surge values in feet, or None if no data
        - future_storm_tide_plot: predicted storm tide values in MLLW feet, or None if no data
    """
    if future_surges_dict is None or len(future_surges_dict) == 0:
        return None, None

    # If a dt doesn't have a surge value, we will use one up to 45 minutes older, since surge values
    # are on the hour.
    def find_nearby_surge(dt):
        surge = None
        min_dt = dt - timedelta(minutes=45)
        while surge is None and dt >= min_dt:
            surge = future_surges_dict.get(dt, None)
            dt -= timedelta(minutes=15)
        return None if surge is None else surge + (future_surge_calc_bias or 0)

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

    def callback(dt):
        if timeline.is_past(dt) or (
            isinstance(timeline, HiloTimeline) and dt not in astro_hilo_dict
        ):
            return None, None
        surge_val, hilo_pred = get_surge_and_hilo_prediction(dt)
        if surge_val is not None and hilo_pred is not None:
            return round(surge_val, 2), round(surge_val + hilo_pred, 2)
        return None, None

    future_surge_plot, future_storm_tide_plot = timeline.build_plots(callback)

    if all(x is None for x in future_surge_plot):
        return None, None

    return future_surge_plot, future_storm_tide_plot


def build_wind_forecast_plots(
    timeline: GraphTimeline, forecast_dict: dict, hilo_event_dict: dict
) -> tuple[list, list]:
    """
    Build lists for forecast wind speed and direction (0-360) which correspond to the timeline.

    Args:
        timeline (GraphTimeline): the timeline
        forecast_dict (dict): forecast data.
        hilo_event_dict (dict): {dt: HighOrLow} all observed or predicted High/Low events for entire timeline,
            used to restrict returned data to only those times if we have a HiloTimeline.

    Returns: tuple[list, list]. Both lists have None in the same indexes -- no partial data.
        - wind speed (mph)
        - wind direction (0-360)
    """
    if len(forecast_dict) == 0:
        return None, None

    def callback(dt):
        if isinstance(timeline, HiloTimeline) and dt not in hilo_event_dict:
            return None, None
        if dt in forecast_dict:
            return (
                forecast_dict[dt].get("mph"),
                forecast_dict[dt].get("dir"),
            )
        return None, None

    forecast_speed_plot, forecast_wind_dir_plot = timeline.build_plots(callback)

    if all(x is None for x in forecast_speed_plot):
        return None, None

    return forecast_speed_plot, forecast_wind_dir_plot
