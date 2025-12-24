import os.path
from datetime import date, datetime, timedelta
from unittest import TestCase

import app.datasource.astrotide as astro
import app.datasource.cdmo as cdmo
import app.station as stn
import app.tzutil as tz
import app.util as util
from app.hilo import ObservedHighOrLow, PredictedHighOrLow
from app.timeline import GraphTimeline, Timeline
from django import setup
from rest_framework.exceptions import APIException

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

csv_location = "/Users/gshannon/dev/work/docker/wntt/datamount/stations"
test_data_path = os.path.dirname(os.path.abspath(__file__))
wells = stn.get_station("welinwq", csv_location)


dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestCdmo(TestCase):
    tzone = tz.eastern  # Do not change, tests use hard-coded times

    def make_sample_dict(self, values) -> dict:
        # We make a 2-hour timeline and fill it with sample valid readings
        timeline = Timeline(
            datetime(2025, 7, 4, 0, tzinfo=self.tzone),
            datetime(2025, 7, 4, 2, tzinfo=self.tzone),
        )
        self.assertEqual(len(values), timeline.length_requested())
        full = {k: v for (k, v) in zip(timeline.get_requested(), values)}
        return {k: v for (k, v) in full.items() if v is not None}

    def test_xml_parse_with_bad_zero_problem(self):
        # Strip out bogus zero level data from cdmo.
        # Values are in NAVD88, so 5.14 = 0 MLLW for Wells station.

        # 1. with no missing data, make sure we don't remove legal zeros.
        values = [8.14, 7.14, 6.14, 5.14, 4.14, 5.14, 6.14, 7.14, 8.14]
        test_dict = self.make_sample_dict(values)
        cleaned = cdmo.clean_tide_data(test_dict, wells)
        self.assertEqual(cleaned, test_dict)

        # 2. zero following out of range data is always removed
        values = [7.1, 6.6, 6.1, 6.5, 6.3, 5.14, 6.1, 5.5, 4.9]
        test_dict = self.make_sample_dict(values)
        cleaned = cdmo.clean_tide_data(test_dict, wells)
        # 6.3 - 5.14 > 1.0
        expected = {k: v for (k, v) in test_dict.items() if v != 5.14}
        self.assertEqual(cleaned, expected)

        # 3. zero following missing data is ok if followed by data in range
        values = [7.1, 6.6, 6.1, 5.5, None, 5.14, 6.1, 6.6, 7.1]
        test_dict = self.make_sample_dict(values)
        cleaned = cdmo.clean_tide_data(test_dict, wells)
        # abs(5.14 - 6.1) <= 1.0
        self.assertEqual(cleaned, test_dict)

        # 4. zero at beginning of data is ok if followed by data in range
        values = [5.14, 6.1, 5.5, 5.2, 5.0, 4.1, 3.6, 2.1, 2.4]
        test_dict = self.make_sample_dict(values)
        cleaned = cdmo.clean_tide_data(test_dict, wells)
        # abs(5.14 - 6.1) <= 1.0
        self.assertEqual(cleaned, test_dict)

        # 5. Combo with 3  zeros in a row
        # 1st 0 is rejected because of gap from previous value
        # 2nd 0 is rejected because 0s on either side
        # 3rd 0 is accepted because good gap on right side
        values = [9.14, 8.14, 7.14, 5.14, 5.14, 5.14, 6.14, 7.14, 8.14]
        test_dict = self.make_sample_dict(values)
        cleaned = cdmo.clean_tide_data(test_dict, wells)
        to_remove = [3, 4]  # These 2 should be rejected
        keys = list(test_dict.keys())
        expected = {k: test_dict[k] for i, k in enumerate(keys) if i not in to_remove}
        self.assertEqual(cleaned, expected)

    def test_hilos_with_predicted_high_on_previous_day(self):
        # Edge case: The last high tide on day 12/20 was at 23:48. Using that as guidance, the max nearby
        # observed tide was on 12/21 at 00:00. That correctly gets marked as high for timeline of
        # that starts on or before the 20th. But when the timeline starts on the 21st, the predicted tides
        # from the 21st do not include the 23:48 high tide from the 20th, and without that the observed high
        # tide at 00:00 would not be annotated. Therefore, we need to always include the day preceding the
        # timeline start when pulling predicted high/lows.

        converter = cdmo.make_navd88_level_converter(wells.navd88_meters_to_mllw_feet)

        # A single-day timeline for the 21st. Remember we pull in extra padding for cdmo tide data.
        timeline = GraphTimeline(date(2025, 12, 20), date(2025, 12, 21), self.tzone)
        with open(f"{test_data_path}/data/cdmo-20251221.xml", "r") as file:
            xml = file.read()
        obs_dict = cdmo.parse_cdmo_xml(timeline, xml, "Level", converter)

        # First, see what happens when we just pull the 21st high/low predictions.
        raw = util.read_file(f"{test_data_path}/data/astro-hilo-20251221.json")
        contents = astro.extract_json(raw)
        pred_hilo_dict = astro.hilo_json_to_dict(wells, contents, timeline.time_zone)
        hilos = cdmo.find_all_hilos(timeline, obs_dict, pred_hilo_dict)
        midnight_high = datetime(2025, 12, 21, 0, tzinfo=self.tzone)
        # The predicted high tide from the 20th is not included in the 21st predictions.
        self.assertNotIn(midnight_high, hilos)

        # But if we include the 20th, we should get the predicted high tide from the 20th.
        raw = util.read_file(f"{test_data_path}/data/astro-hilo-20251220-21.json")
        contents = astro.extract_json(raw)
        pred_hilo_dict = astro.hilo_json_to_dict(wells, contents, timeline.time_zone)
        hilos = cdmo.find_all_hilos(timeline, obs_dict, pred_hilo_dict)
        midnight_high = datetime(2025, 12, 21, 0, tzinfo=self.tzone)
        self.assertIn(midnight_high, hilos)

    def test_hilos_with_missing_data(self):
        # With seven hours of missing observed data, make sure all highs and lows are still found.
        timeline = GraphTimeline(date(2025, 12, 4), date(2025, 12, 5), self.tzone)

        # Get astro predictions for the timeline
        raw = util.read_file(f"{test_data_path}/data/astro-hilo-120405.json")
        contents = astro.extract_json(raw)
        pred_hilo_dict = astro.hilo_json_to_dict(wells, contents, timeline.time_zone)

        # Get observed tides from CDMO for the timeline
        with open(f"{test_data_path}/data/cdmo-120405.xml", "r") as file:
            xml = file.read()
        converter = cdmo.make_navd88_level_converter(wells.navd88_meters_to_mllw_feet)
        obs_dict = cdmo.parse_cdmo_xml(timeline, xml, "Level", converter)

        # Find the hilos in the observed data.
        hilos = cdmo.find_all_hilos(timeline, obs_dict, pred_hilo_dict)
        self.assertEqual(len(hilos), len(pred_hilo_dict))
        missing_obs = datetime(2025, 12, 5, 4, 15, tzinfo=self.tzone)
        self.assertNotIn(missing_obs, obs_dict)
        self.assertIsInstance(hilos[missing_obs], PredictedHighOrLow)
        for dt, event in hilos.items():
            if dt != missing_obs:
                self.assertIsInstance(event, ObservedHighOrLow)

        for dt, val in hilos.items():
            if isinstance(val, ObservedHighOrLow):
                self.assertIn(dt, obs_dict)
            else:
                self.assertEqual(val.value, pred_hilo_dict[dt].value)

    def test_cdmo_invalid_ip(self):
        xml = self.load_xml("cdmo-invalid-ip.xml")
        timeline = GraphTimeline(date(2025, 3, 31), date(2025, 3, 31), self.tzone)
        with self.assertRaisesRegex(APIException, "^Invalid ip"):
            cdmo.parse_cdmo_xml(timeline, xml, "anyparam", None)

    def test_handle_navd88(self):
        converter = cdmo.make_navd88_level_converter(wells.navd88_meters_to_mllw_feet)
        self.assertTrue(converter(None, None) is None)
        self.assertTrue(cdmo.handle_windspeed("nONE", None) is None)
        self.assertTrue(converter("", None) is None)
        self.assertTrue(converter("13s", None) is None)
        self.assertTrue(converter("\n\t", None) is None)

        max_meters = wells.mllw_feet_to_navd88_meters(cdmo.max_tide)
        min_meters = wells.mllw_feet_to_navd88_meters(cdmo.min_tide)
        self.assertTrue(converter(f"{max_meters + 1.0}", None) is None)
        self.assertTrue(converter(f"{max_meters - 1.0}", None) is not None)
        self.assertTrue(converter(f"{min_meters - 1.0}", None) is None)
        self.assertTrue(converter(f"{min_meters + 1.0}", None) is not None)
        self.assertEqual(
            converter("1.5", None),
            wells.navd88_meters_to_mllw_feet(1.5),
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
