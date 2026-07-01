import logging
from datetime import date

from app import graph_plot as gp
from app import util
from app.datasource import astrotide as astro
from app.datasource import cdmo, syzygy
from app.datasource import surge as sg
from app.datasource import windforecast as wind
from app.hilo import PredictedHighOrLow
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
    astro_preds15_dict = astro.get_15m_astro_tides(
        station.noaa_station_id, timeline, station.navd88_feet_to_mllw_feet, True
    )

    # Get wind forecasts.
    forecast_wind_dict = wind.get_wind_forecast(station, timeline, hilo_mode)

    # Get astronomical tide predictions
    astro_all_hilo_dict = astro.get_hilo_astro_tides(
        station.noaa_station_id, timeline, station.navd88_feet_to_mllw_feet, True
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
            timeline.add_syzygy_time(dt)

    # Phase 2. Now we have all the data we need, in dense dictionaries. Build the lists required
    # by the graph plots, which must be the same length as the timeline so the front end can graph them.
    # They are sparse rather than dense -- they have None for any missing data.

    hist_tides_plot, hist_tides_label_plot = gp.build_hist_tide_plot(
        timeline, water_dict, hilo_event_dict
    )

    wind_speed_plot, wind_gust_plot, wind_dir_plot = gp.build_wind_plots(
        timeline, wind_dict, hilo_event_dict
    )

    astro_tides_plot, astro_label_plot = gp.build_astro_plot(
        timeline, astro_preds15_dict, hilo_event_dict
    )

    past_surge_plot = gp.build_past_surge_plot(
        timeline, past_surge_dict, hilo_event_dict
    )

    forecast_wind_speed_plot, forecast_wind_dir_plot = gp.build_wind_forecast_plots(
        timeline, forecast_wind_dict
    )

    future_surge_plot, future_storm_tide_plot = gp.build_future_surge_plots(
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
                if isinstance(val, PredictedHighOrLow)
                # This means there was no observed value, else it would have been an ObservedHighOrLow.
                # So we'll use the actual prediction time.
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
        "hist-tides-labels": hist_tides_label_plot,
        "wind-dir": wind_dir_plot,
        "astro-tides-labels": astro_label_plot,
        "forecast-wind-dir": forecast_wind_dir_plot,
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
        # This group is sparse data for the actual plots shown on the chart, with Nones for missing data.
        "dimensions": keys,
        "blob": blob,
        # These do not fit into the basic plot model
        "syzygy": {dt.isoformat(): val for (dt, val) in syzygy_dict.items()},
        "subtitle": subtitle,
        "highest_annual_prediction": stn.get_astro_high_tide_mllw(
            station, start_date.year
        ),
    }


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
