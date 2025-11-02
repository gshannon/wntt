import os.path
from datetime import date, datetime, timedelta
from unittest import TestCase

import app.datasource.cdmo as cdmo
import app.tzutil as tz
import app.util as util
from app.timeline import GraphTimeline, Timeline
from rest_framework.exceptions import APIException

dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)
noaa_station_id = "8419317"


class TestCdmo(TestCase):
    tzone = tz.eastern  # Do not change, tests use hard-coded times

    def test_calculate_hilos_simple(self):
        """High/Low detection works properly with small data sets"""

        def build_test_data(tides, start_date=date(2025, 1, 1)):
            end_date = start_date + timedelta(days=(int(len(tides) / 96)))
            timeline = GraphTimeline(start_date, end_date, self.tzone)
            d = dict(zip(timeline._requested_times, tides))  # no None's in datadict
            datadict = {key: val for key, val in d.items() if val is not None}
            return timeline, datadict

        # Single data value
        tides = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        timeline, _ = build_test_data(tides)
        datadict = {datetime(2025, 1, 1): 8}
        self.assertEqual(cdmo.find_hilos(timeline, datadict), {})

        # Minimal Low only
        tides = [None, 4, 3, 4, None, 10]
        timeline, datadict = build_test_data(tides)
        expected_hilos = {
            datetime(2025, 1, 1, 0, 30, tzinfo=self.tzone): "L",
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

        # Minimal High only
        tides = [None, 9, 10, 9, None, 3]
        timeline, datadict = build_test_data(tides)
        expected_hilos = {
            datetime(2025, 1, 1, 0, 30, tzinfo=self.tzone): "H",
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

        # Minimal high and low
        tides = [None, 4, 3, 4, None, 9, 10, 9, None]
        timeline, datadict = build_test_data(tides)
        expected_hilos = {
            datetime(2025, 1, 1, 0, 30, tzinfo=self.tzone): "L",
            datetime(2025, 1, 1, 1, 30, tzinfo=self.tzone): "H",
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

        # Highs and lows are on the edge, no opposite direction detected
        tides = [3, 4, 5, 6, 7, 8, 9, 10]
        timeline, datadict = build_test_data(tides)
        self.assertEqual(cdmo.find_hilos(timeline, datadict), {})

        # high and low both compromised by None
        # fmt: off
        tides = [8, 9, 10, 10, None, None, None, None, None, 9, 8, 7, 5, 4, 3, None, None, None, None, None, 2, 2, 3, 4]
        # fmt: on
        timeline, datadict = build_test_data(tides)
        self.assertEqual(cdmo.find_hilos(timeline, datadict), {})

        # actual data from 3/1/2025
        # fmt: off
        tides = [
            9.8, 9.62, 9.371, 9.01, 8.58, 8.12, 7.57, 6.975, 6.31, 5.66, 4.975, 4.25, 3.524, 2.78, 2.09,
            1.427, 0.8701, 0.2175, -0.010675, -0.3701, -0.7002, -0.8301, -0.8301, -0.9306, -0.8301, -0.47064, -0.2402,
            0.0886, 0.5801, 1.137, 1.697, 2.286, 2.935, 3.657, 4.31, 5.10, 5.725, 6.44, 7.17, 7.85, 8.42, 8.98,
            9.34, 9.7, 10, 10.29, 10.52, 10.621, 10.68, 10.64, 10.48, 10.26, 9.89, 9.54, 9.14, 8.58, 7.95, 7.27,
            6.52, 5.76, 5.01, 4.29, 3.564, 2.738, 2.016, 1.266, 0.806, 0.185, -0.11032, -0.5, -0.7705, -0.7304, -1.1904,
            -0.7002, -0.7304, -0.47064, -0.11032, 0.1201, 0.677, 1.064, 1.657, 2.32, 2.907, 3.697, 4.29, 4.88, 5.52,
            6.35, 7.03, 7.725, 8.26, 8.71, 9.14, 9.41, 9.7, 9.86, 9.93
        ]
        # fmt: on
        timeline, datadict = build_test_data(tides, date(2025, 3, 1))
        expected_hilos = {
            datetime(2025, 3, 1, 5, 45, tzinfo=self.tzone): "L",
            datetime(2025, 3, 1, 12, 0, tzinfo=self.tzone): "H",
            datetime(2025, 3, 1, 18, 0, tzinfo=self.tzone): "L",
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

    def test_calculate_hilos_full(self):
        """High/Low detetion works properly with complete day of data"""
        xml = self.load_xml("cdmo-level.xml")
        timeline = GraphTimeline(date(2025, 3, 31), date(2025, 3, 31), self.tzone)
        converter = cdmo.make_navd88_level_converter("8419317")
        datadict = cdmo.get_cdmo_data(timeline, xml, cdmo.tide_param, converter)
        expected = {
            datetime(2025, 3, 31, 0, 45, tzinfo=self.tzone): "H",
            datetime(2025, 3, 31, 7, 0, tzinfo=self.tzone): "L",
            datetime(2025, 3, 31, 13, 15, tzinfo=self.tzone): "H",
            datetime(2025, 3, 31, 19, 0, tzinfo=self.tzone): "L",
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected)

    def test_calculate_hilos_with_hi_on_boundary(self):
        """High/Low detetion works properly with high at midnight"""
        xml = self.load_xml("cdmo-level-1d.xml")
        timeline = GraphTimeline(date(2025, 10, 22), date(2025, 10, 22), self.tzone)
        converter = cdmo.make_navd88_level_converter("8419317")
        datadict = cdmo.get_cdmo_data(timeline, xml, cdmo.tide_param, converter)
        expected = {
            datetime(2025, 10, 22, 0, 0, tzinfo=self.tzone): "H",
            datetime(2025, 10, 22, 6, 15, tzinfo=self.tzone): "L",
            datetime(2025, 10, 22, 12, 30, tzinfo=self.tzone): "H",
            datetime(2025, 10, 22, 18, 30, tzinfo=self.tzone): "L",
            # This last one is outside the timeline, but was retrieve as padding. It's
            # silently ignored.
            datetime(2025, 10, 23, 0, 45, tzinfo=self.tzone): "H",
        }
        actual = cdmo.find_hilos(timeline, datadict)
        self.assertEqual(actual, expected)

    def test_calculate_hilos_with_nones(self):
        """High/Low detetion works properly with 1 hour missing"""
        xml = self.load_xml("cdmo-level-2d.xml")
        timeline = GraphTimeline(date(2025, 10, 21), date(2025, 10, 22), self.tzone)
        converter = cdmo.make_navd88_level_converter("8419317")
        datadict = cdmo.get_cdmo_data(timeline, xml, cdmo.tide_param, converter)
        # Note extra highs at beginning and end, from the padding.
        expected = {
            datetime(2025, 10, 20, 23, 30, tzinfo=self.tzone): "H",
            datetime(2025, 10, 21, 5, 45, tzinfo=self.tzone): "L",
            datetime(2025, 10, 21, 11, 45, tzinfo=self.tzone): "H",
            datetime(2025, 10, 21, 18, 0, tzinfo=self.tzone): "L",
            # This high had 4 Nones next to it.
            datetime(2025, 10, 22, 0, 0, tzinfo=self.tzone): "H",
            datetime(2025, 10, 22, 6, 15, tzinfo=self.tzone): "L",
            datetime(2025, 10, 22, 12, 30, tzinfo=self.tzone): "H",
            datetime(2025, 10, 22, 18, 30, tzinfo=self.tzone): "L",
            datetime(2025, 10, 23, 0, 45, tzinfo=self.tzone): "H",
        }
        actual = cdmo.find_hilos(timeline, datadict)
        self.assertEqual(actual, expected)

    def test_cdmo_invalid_ip(self):
        xml = self.load_xml("cdmo-invalid-ip.xml")
        timeline = GraphTimeline(date(2025, 3, 31), date(2025, 3, 31), self.tzone)
        with self.assertRaisesRegex(APIException, "^Invalid ip"):
            cdmo.get_cdmo_data(timeline, xml, "anyparam", None)

    def test_handle_navd88(self):
        converter = cdmo.make_navd88_level_converter("8419317")
        self.assertTrue(converter(None, None) is None)
        self.assertTrue(cdmo.handle_windspeed("nONE", None) is None)
        self.assertTrue(converter("", None) is None)
        self.assertTrue(converter("13s", None) is None)
        self.assertTrue(converter("\n\t", None) is None)

        max_meters = util.mllw_feet_to_navd88_meters(cdmo.max_tide, noaa_station_id)
        min_meters = util.mllw_feet_to_navd88_meters(cdmo.min_tide, noaa_station_id)
        self.assertTrue(converter(f"{max_meters + 1.0}", None) is None)
        self.assertTrue(converter(f"{max_meters - 1.0}", None) is not None)
        self.assertTrue(converter(f"{min_meters - 1.0}", None) is None)
        self.assertTrue(converter(f"{min_meters + 1.0}", None) is not None)
        self.assertEqual(
            converter("1.5", None),
            util.navd88_meters_to_mllw_feet(1.5, noaa_station_id),
        )

    def test_handle_windspeed(self):
        self.assertTrue(cdmo.handle_windspeed(None, None) is None)
        self.assertTrue(cdmo.handle_windspeed("nONe", None) is None)
        self.assertTrue(cdmo.handle_windspeed("", None) is None)
        self.assertTrue(cdmo.handle_windspeed("7..3", None) is None)
        self.assertTrue(cdmo.handle_windspeed("\n\t", None) is None)
        self.assertTrue(cdmo.handle_windspeed("-0.5", None) is None)
        self.assertTrue(cdmo.handle_windspeed("121.0", None) is None)
        self.assertEqual(
            cdmo.handle_windspeed("13.3", None), util.meters_per_second_to_mph(13.3)
        )

    def test_cdmo_dates_graph_standard(self):
        """In standard time, no changes are needed for any time zone."""
        # January is in Standard time. Graph timelines have 00:00 of next full day added.
        start_date = date(2024, 1, 10)
        end_date = date(2024, 1, 12)
        for tzone in [tz.central, tz.mountain, tz.pacific]:
            timeline = GraphTimeline(start_date, end_date, tzone)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (start_date, end_date + timedelta(days=1)),
            )

    def test_cdmo_dates_spring_forward(self):
        """If timeline starts in standard but ends in DST, handle all scenarios"""
        # start date doesn't change, end date is bumped back if < 01:00
        for zone in [tz.central, tz.mountain, tz.pacific]:
            start_dt = datetime(2025, 3, 9, 0, tzinfo=zone)
            end_dt = datetime(2025, 3, 10, 0, tzinfo=zone)
            timeline = Timeline(start_dt, end_dt)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (start_dt.date(), end_dt.date() - timedelta(days=1)),
            )

        # start date doesn't change, neither does end date if >= 01:00
        for zone in [tz.central, tz.mountain, tz.pacific]:
            start_dt = datetime(2025, 3, 9, 0, tzinfo=zone)
            end_dt = datetime(2025, 3, 10, 1, tzinfo=zone)
            timeline = Timeline(start_dt, end_dt)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (start_dt.date(), end_dt.date()),
            )

    def test_cdmo_dates_fall_back(self):
        """If timeline starts in DST but ends in standard, handle all scenarios"""
        # start time with hour < 0 is bumped back a day, end date is unchanged
        for zone in [tz.central, tz.mountain, tz.pacific]:
            start_dt = datetime(2025, 10, 2, 0, tzinfo=zone)
            end_dt = datetime(2025, 10, 2, 23, 45, tzinfo=zone)
            timeline = Timeline(start_dt, end_dt)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (start_dt.date() - timedelta(days=1), end_dt.date()),
            )

        # start time with hour > 0 is left alone, end date is unchanged
        for zone in [tz.central, tz.mountain, tz.pacific]:
            start_dt = datetime(2025, 10, 2, 1, tzinfo=zone)
            end_dt = datetime(2025, 10, 2, 23, 45, tzinfo=zone)
            timeline = Timeline(start_dt, end_dt)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (start_dt.date(), end_dt.date()),
            )

    def test_cdmo_dates_daylight_savings_for_graph(self):
        """In DST, if first datetime is at midnight, start date is moved back one day regardless of zone."""
        # July is in DST
        start_date = date(2024, 7, 10)
        end_date = date(2024, 7, 10)
        expected_start_date = start_date - timedelta(days=1)
        for tzone in [tz.central, tz.mountain, tz.pacific]:
            timeline = GraphTimeline(start_date, end_date, tzone)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (expected_start_date, end_date),
            )
            timeline = GraphTimeline(start_date, end_date, tzone)
            self.assertEqual(
                cdmo.compute_cdmo_request_dates(timeline.start_dt, timeline.end_dt),
                (expected_start_date, end_date),
            )

    def load_xml(self, filename):
        path = os.path.dirname(os.path.abspath(__file__))
        return util.read_file(f"{path}/data/{filename}")
