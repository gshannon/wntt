import logging
from datetime import date, datetime, timedelta

from app import util
from app.aux_data import AuxData, AuxDataType
from app.datasource import astrotide as astro
from app.datasource import cdmo, syzygy
from app.datasource import surge as sg
from app.datasource import windforecast as wind
from app.hilo import Hilo, ObservedHighOrLow, PredictedHighOrLow
from app.timeline import GraphTimeline, HiloTimeline

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
    start_date: date,
    end_date: date,
    hilo_mode: bool,
    station: stn.Station,
    special: bool,
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
    syzygy_dict = syzygy.get_syzygy_data(timeline)
    # Phase 1: Retrieve all data from external sources. All these dicts are dense -- they
    # only have keys for actual data, not None, and are keyed by the datetime from the timeline.

    # Start with the observed tide data and wind data, which may be useful in gathering other data.
    water_dict = cdmo.get_water_data(station, timeline)
    wind_dict = cdmo.get_wind_data(station, timeline)

    # Get 15-minute interval astronomical tide predictions for the entire timeline.
    astro_preds15_dict = astro.get_15m_astro_tides(station, timeline)

    # Get wind forecasts.
    forecast_wind_dict = wind.get_wind_forecast(station, timeline, hilo_mode)

    # Pull all predicted high & low tides for the timeline. If the timeline starts in the past, it may
    # include tide observations, and since we use predicted highs/lows to annotate observed highs/lows, we will
    # need to pull in data for the day before the timeline to handle certain edge cases where a high or low
    # occurs just before the start of the timeline.
    hilo_start_date = (
        timeline.start_dt.date() - timedelta(days=1)
        if timeline.is_past(timeline.start_dt)
        else timeline.start_dt.date()
    )
    astro_all_hilo_dict = astro.get_hilo_astro_tides(
        station, hilo_start_date, timeline.end_dt.date()
    )

    # Determine all highs and lows, whether observed or predicted.
    hilo_event_dict = cdmo.find_all_hilos(timeline, water_dict, astro_all_hilo_dict)

    if hilo_mode:
        # The HiloTimeline needs to keep track of these for later processing.
        timeline.register_hilo_times(list(hilo_event_dict.keys()))

    past_surge_dict = sg.calculate_past_storm_surge(astro_preds15_dict, water_dict)

    future_surge_dict = sg.get_future_surge_data(
        timeline,
        station.noaa_station_id,
        max(water_dict) if len(water_dict) > 0 else None,
    )

    # Before we start building plots, add all syzygy events to the timeline
    # so they can be shown at their precise times.
    if len(syzygy_dict) > 0:
        for dt in syzygy_dict:
            timeline.add_time(dt)

    # Phase 2. Now we have all the data we need, in dense dictionaries. Build the lists required
    # by the graph plots, which must be the same length as the timeline so the front end can graph them.
    # They are sparse rather than dense -- they have None for any missing data.

    aux_data = AuxData()
    hist_tides_plot = build_hist_tide_plot(
        timeline, water_dict, hilo_event_dict, aux_data
    )

    wind_speed_plot, wind_gust_plot = build_wind_plots(timeline, wind_dict, aux_data)

    forecast_wind_speed_plot = build_wind_forecast_plots(
        timeline, forecast_wind_dict, aux_data
    )

    astro_tides_plot = build_astro_plot(
        timeline, astro_preds15_dict, hilo_event_dict, aux_data
    )

    past_storm_surge_check_plot = None
    past_storm_tide_check_plot = None
    past_storm_surge_check_bias1_plot = None
    past_storm_tide_check_bias1_plot = None
    past_storm_surge_check_bias2_plot = None
    past_storm_tide_check_bias2_plot = None

    # if special:
    #     past_surge_check_dict = sg.get_best_historic_surge(
    #         timeline, station.noaa_station_id, None
    #     )
    #     past_surge_check_bias1_dict = sg.get_best_historic_surge(
    #         timeline, station.noaa_station_id, 1
    #     )
    #     past_surge_check_bias2_dict = sg.get_best_historic_surge(
    #         timeline, station.noaa_station_id, 2
    #     )

    #     past_storm_surge_check_plot, past_storm_tide_check_plot = (
    #         build_past_surge_check_plots(
    #             timeline, past_surge_check_dict, astro_preds15_dict
    #         )
    #     )

    #     past_storm_surge_check_bias1_plot, past_storm_tide_check_bias1_plot = (
    #         build_past_surge_check_plots(
    #             timeline, past_surge_check_bias1_dict, astro_preds15_dict
    #         )
    #     )

    #     past_storm_surge_check_bias2_plot, past_storm_tide_check_bias2_plot = (
    #         build_past_surge_check_plots(
    #             timeline, past_surge_check_bias2_dict, astro_preds15_dict
    #         )
    #     )

    past_surge_plot = (
        timeline.build_plot(lambda dt: past_surge_dict.get(dt, None))
        if not timeline.is_all_future()
        else None
    )

    future_surge_plot, future_storm_tide_plot = build_future_surge_plots(
        timeline,
        future_surge_dict.get("surges", None),
        # TODO: enable this once we like this approach
        # future_surge_dict.get("bias1 or bias2"),
        None,
        astro_preds15_dict,
        astro_all_hilo_dict,
    )

    # If we've prepared any predicted high or low tides times, which have actual times rather than the nearest
    # 15-min time, we want to replace those timeline times with the real times, so they show accurately on the graph.
    # Since the timeline is just a list of datetimes and the plots are a list of data values or None, all we have to
    # do is replace those values in the timeline, and then return the timeline with the plots.
    if len(hilo_event_dict) > 0:
        final_timeline = timeline.get_final_times(
            {
                key: val.real_dt
                for key, val in hilo_event_dict.items()
                # This means there was no observed value, else it would have been an ObservedHighOrLow.
                # So we'll use the actual prediction time even if it's in the past.
                if isinstance(val, PredictedHighOrLow)
            }
        )
    else:
        final_timeline = timeline.requested_times
    start_date_str = timeline.start_date.strftime("%b %-d, %Y")
    end_date_str = timeline.end_date.strftime("%b %-d, %Y")
    subtitle = (
        start_date_str
        if start_date == end_date
        else f"{start_date_str} - {end_date_str}"
    )

    driver = {
        "hist-tides": hist_tides_plot,
        "astro-tides": astro_tides_plot,
        "wind-speeds": wind_speed_plot,
        "wind-gusts": wind_gust_plot,
        "past-surge": past_surge_plot,
        "forecast-wind-speeds": forecast_wind_speed_plot,
        "future-tide": future_storm_tide_plot,
        "future-surge": future_surge_plot,
    }

    keys = ["dt"]
    for k, plot in driver.items():
        if plot is not None:
            keys.append(k)

    blob = []
    for ndx, dt in enumerate(final_timeline):
        row = [dt]
        for k, plot in driver.items():
            if plot is not None:
                row.append(plot[ndx])
        blob.append(row)

    return {
        "timeline": final_timeline,
        # This group is sparse data for the actual plots shown on the chart, with Nones for missing data.
        "dimensions": keys,
        "blob": blob,
        # These do not fit into the basic plot model
        "syzygy": {dt.isoformat(): val for (dt, val) in syzygy_dict.items()},
        "subtitle": subtitle,
        "highest_annual_prediction": stn.get_astro_high_tide_mllw(
            station, start_date.year
        ),
        # This is datetime-based auxilary data used as lookups for various annotations in the chart. For these we'll build a
        # dense dict keyed by the datetime.  Note that json doesn't support datetime as object keys so we convert to ISO strings.
        "aux_data": {dt.isoformat(): val for (dt, val) in aux_data.data.items()},
    }
    #     "past_surge": past_surge_plot,
    # "past_storm_surge_check": past_storm_surge_check_plot,
    # "past_storm_tide_check": past_storm_tide_check_plot,
    # "past_storm_surge_check_bias1": past_storm_surge_check_bias1_plot,
    # "past_storm_tide_check_bias1": past_storm_tide_check_bias1_plot,
    # "past_storm_surge_check_bias2": past_storm_surge_check_bias2_plot,
    # "past_storm_tide_check_bias2": past_storm_tide_check_bias2_plot,
    # }


def build_hist_tide_plot(
    timeline: GraphTimeline, water_dict: dict, hilo_event_dict: dict, aux_data: AuxData
) -> tuple[list, list]:
    """Build historical tide plot and high or low tide labels. For timelines entirely in the future,
    each callback would return None, so we can just return None for both lists.

    Args:
        timeline (GraphTimeline): the timeline
        water_dict: dense dict of observed tide readings {datetime: {"level": val, "temp": val"}}
        hilo_event_dict: dense dict of all high/low tides, {timeline_dt: HighOrLow}
        aux_data: AuxData instance to be populated with any aux data we want to return to the app.


    Returns:
        tuple[list, list]:
        - hist_tides_plot: list of historical tide heights in MLLW feet, or None if no data
    """

    if timeline.is_all_future():
        return None

    def get_hilo_label(dt: datetime):
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            # If it's a PredictedHighOrLow, we don't want to annotate on the historical plot.
            if isinstance(event, ObservedHighOrLow):
                aux_data.add(
                    dt,
                    AuxDataType.OBSERVED_HILO,
                    "(HIGH)" if event.hilo == Hilo.HIGH else "(LOW)",
                )
        return ""

    def get_tide(dt: datetime):
        if dt in water_dict:
            return water_dict[dt][cdmo.Param.Tide.label]
        else:
            return None

    hist_tides_plot = timeline.build_plot(get_tide)
    timeline.build_plot(get_hilo_label)
    return hist_tides_plot


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


def build_wind_forecast_plots(
    timeline: GraphTimeline, forecast_dict: dict, aux_data: AuxData
) -> list:
    """
    Build data for 3 graph plots for wind forecast -- speed, direction (degrees), and direction label (e.g. NNE).

    Args:
        timeline (GraphTimeline): the timeline
        forecast_dict (dict): forecast data.

    Returns:
        forecast_wind_speed_plot:
    Side-effects:
        * Wind direction (0-360, to drive marker angle) added to aux_data with key "FWD"
        * Wind direction string (for hover text display) added to aux_data with key "FWDS"
    """
    if len(forecast_dict) == 0:
        return None

    found = False

    def get_value(dt):
        nonlocal found
        if dt in forecast_dict:
            found = True
            return forecast_dict[dt].get("mph")
        return None

    def get_dir_degrees(dt):
        if dt in forecast_dict:
            aux_data.add(
                dt, AuxDataType.FORECAST_WIND_DIR, forecast_dict[dt].get("dir")
            )
        return None

    def get_dir_label(dt):
        if dt in forecast_dict:
            aux_data.add(
                dt,
                AuxDataType.FORECAST_WIND_DIR_STR,
                forecast_dict[dt].get("dir_str"),
            )
        return None

    forecast_speed_plot = timeline.build_plot(get_value)
    timeline.build_plot(get_dir_degrees)
    timeline.build_plot(get_dir_label)

    if not found:
        return None

    return forecast_speed_plot


def build_astro_plot(
    timeline: GraphTimeline,
    reg_preds_dict: dict,
    hilo_event_dict: dict,
    aux_data: AuxData,
) -> list:
    """
    Builds plots for the astronomical tide data. We essentially merge the regular 15-min predictions and the
    hilo data, preferring the hilo value if present, which is more accurate.

    Args:
        timeline (GraphTimeline): the time line
        reg_preds_dict (dict): {dt: value} for 15-min predictions over entire timeline
        hilo_event_dict (dict): {dt: HighOrLow} High/Low predictions after last observed.

    Returns:
        - Matching plot data for the astronomical tide values, including Nones where data is missing (unlikely).
    Side-effects:
        * Aux data is populated with HiLo annotation labels, keyed by datetime
    """

    def get_value(dt):
        # For value, prefer the predicted hilo value if present, else use the 15-min prediction.
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            # ignore it if it's an ObservedHighOrLow
            if isinstance(event, PredictedHighOrLow):
                return event.value
        return reg_preds_dict.get(dt, None)

    def get_label(dt):
        if dt in hilo_event_dict:
            event = hilo_event_dict[dt]
            if isinstance(event, PredictedHighOrLow):
                aux_data.add(
                    event.real_dt,
                    AuxDataType.ASTRO_HILO,
                    "(HIGH)" if event.hilo == Hilo.HIGH else "(LOW)",
                )
        return ""

    astro_tides_plot = timeline.build_plot(get_value)
    timeline.build_plot(get_label)

    return astro_tides_plot


def build_wind_plots(
    timeline: GraphTimeline, wind_dict: dict, aux_data: AuxData
) -> tuple[list, list]:
    """Convert the recorded wind data to 4 plots for Plotly scatter plots.

    Args:
        timeline (GraphTimeline): timeline
        wind_dict (dict): {dt: {'speed': x, 'gust': x, 'dir_deg': x, 'dir_str': x}}

    Returns:
        1. Wind speed plot
        2. Wind gust plot

    Side-effects:
        * Wind direction (0-360, to drive marker angle) added to aux_data with key "WD"
        * Wind direction string (for hover text display) added to aux_data with key "WDS"
    """

    if len(wind_dict) == 0:
        # There are no wind predictions, return None for all lists.
        return None, None

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
        val = check_item(dt, cdmo.Param.WindDir.label)
        if val is not None:
            aux_data.add(dt, AuxDataType.OBSERVED_WIND_DIR, val)
        return ""

    def check_dir_str(dt):
        val = check_item(dt, cdmo.WIND_DIRSTR_LABEL)
        if val is not None:
            aux_data.add(dt, AuxDataType.OBSERVED_WIND_DIR_STR, val)
        return ""

    wind_speed_plot = timeline.build_plot(check_speed)
    wind_gust_plot = timeline.build_plot(check_gust)
    timeline.build_plot(check_dir)
    timeline.build_plot(check_dir_str)

    if not found:
        return None, None

    return wind_speed_plot, wind_gust_plot


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
        raise util.InternalError(
            "%s - %s is not between %s - %s" % (start, end, earliest_date, latest_date)
        )
    if end < start:
        raise util.InternalError(
            "end_date %s cannot be earlier than start_date %s" % (end, start)
        )
