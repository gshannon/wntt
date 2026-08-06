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

logger = logging.getLogger(__name__)


def get_graph_data(
    start_date: date,
    end_date: date,
    hilo_mode: bool,
    station: stn.Station,
    special: bool,
):
    """Generate data for an ECharts graph.

    Args:
        start_date (date): First day of data
        end_date (date): Last day of data (may be same as first). 00:00 of following day will be added
            automatically to give the graph a better right-hand boundary.
        hilo_mode (bool): If true, data will include only high and low tide data points.
        station (Station): Station for which to get data

    Returns:
        dict: All data required for graph, convertible to json
    """

    validate_dates(start_date, end_date)

    if hilo_mode:
        timeline = HiloTimeline(start_date, end_date, station.time_zone)
    else:
        timeline = GraphTimeline(start_date, end_date, station.time_zone)

    # Get moon/sun tide data
    syzygy_list = syzygy.get_syzygy_data(timeline)
    # Phase 1: Retrieve all data from external sources. All these dicts are dense -- they
    # only have keys for actual data, not None, and are keyed by the datetime from the timeline.

    # Start with the observed tide data and wind data, which may be useful in gathering other data.
    obs_tides = cdmo.get_water_data(station, timeline)
    obs_winds = cdmo.get_wind_data(station, timeline)

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
    hilo_event_dict = cdmo.find_all_hilos(timeline, obs_tides, astro_all_hilo_dict)

    if hilo_mode:
        # The HiloTimeline needs to keep track of these for later processing.
        timeline.register_hilo_times(list(hilo_event_dict.keys()))

    past_surge_dict = sg.get_recorded_storm_surge(astro_preds15_dict, obs_tides)

    future_surge_dict = sg.get_future_surge_data(
        timeline,
        station.noaa_station_id,
        max(obs_tides) if len(obs_tides) > 0 else None,
    )

    # Phase 2. Now we have all the data we need, in dense dictionaries. Build the lists required
    # by the graph plots, which must be the same length as the timeline so the front end can graph them.
    # They are sparse rather than dense -- they have None for any missing data.

    hist_tides_plot, hist_tides_label_plot = gp.build_observed_tide_plot(
        timeline, obs_tides, hilo_event_dict
    )

    wind_speed_plot, wind_gust_plot, wind_dir_plot = gp.build_wind_plots(
        timeline, obs_winds, hilo_event_dict
    )

    astro_tides_plot, astro_label_plot = gp.build_astro_plot(
        timeline, astro_preds15_dict, hilo_event_dict
    )

    past_surge_plot = gp.build_past_surge_plot(
        timeline, past_surge_dict, hilo_event_dict
    )

    forecast_wind_speed_plot, forecast_wind_dir_plot = gp.build_wind_forecast_plots(
        timeline, forecast_wind_dict, hilo_event_dict
    )

    future_surge_plot, future_storm_tide_plot = gp.build_future_surge_plots(
        timeline,
        future_surge_dict.get("surges", None),
        # TODO: future_surge_dict.get("bias1" or "bias2"),
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

    # Phase 3. Build the final data structure to return.
    plots = {
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

    # Dimensions are the names of each column, in order.
    dimensions = ["dt"] + [k for k in plots if plots[k] is not None]

    # Each blob entry represents a "column" of data, with the first value being the datetime and
    # the rest being all the data for that time, in the same order as the dimensions.
    blob = []
    for ndx, dt in enumerate(final_timeline):
        blob.append([dt] + [plots[k][ndx] for k in plots if plots[k] is not None])

    return {
        "dimensions": dimensions,
        "blob": blob,
        # The rest is auxiliary data. Note we have to convert datetimes that are used as dict keys, or else the
        # json serialization will fail. Keys have to be scalars, not objects.
        "syzygy": syzygy_list,
        "subtitle": build_subtitle(start_date, end_date),
        "highest_annual_prediction": stn.get_astro_high_tide_mllw(
            station, start_date.year
        ),
    }


def build_subtitle(start_date, end_date) -> str:
    # Build a subtitle for the graph, based on the start and end dates.
    start_date_str = start_date.strftime("%b %-d, %Y")
    end_date_str = end_date.strftime("%b %-d, %Y")
    return (
        start_date_str
        if start_date == end_date
        else f"{start_date_str} - {end_date_str}"
    )


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
            f"{start} - {end} is not between {earliest_date} - {latest_date}"
        )
    if end < start:
        raise util.InternalError(
            f"end_date {end} cannot be earlier than start_date {start}"
        )
