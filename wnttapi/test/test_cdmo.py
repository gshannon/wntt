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
station = stn.get_station("welinwq", csv_location)


dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestCdmo(TestCase):
    tzone = tz.eastern  # Do not change, tests use hard-coded times

    def test_xml_parse_with_bad_zero_problem(self):
        # Strip out bogus zero level data from cdmo.
        timeline = Timeline(
            datetime(2025, 12, 8, 0, tzinfo=self.tzone),
            datetime(2025, 12, 8, 3, tzinfo=self.tzone),
            datetime(2025, 12, 9, 0, tzinfo=self.tzone),
        )
        # Create test dict for timeline, setting all values to any non-zero value.
        full_dict = dict.fromkeys(timeline.get_all_past(), 2.7)
        # Remove all 1 o'clock data and set 2:00, 2:15 and 2:45 to 0
        test_dict = {k: v for k, v in full_dict.items() if k.hour != 1}
        bad_date1 = datetime(2025, 12, 8, 2, 0, tzinfo=self.tzone)
        bad_date2 = datetime(2025, 12, 8, 2, 15, tzinfo=self.tzone)
        ok_zero_date = datetime(2025, 12, 8, 2, 45, tzinfo=self.tzone)
        test_dict[bad_date1] = test_dict[bad_date2] = test_dict[ok_zero_date] = (
            station.mllw_conversion
        )
        # clean it. It should remove only the 2 zero elements following the data gap.
        cleaned = cdmo.clean_water_data(test_dict, station)
        self.assertEqual(len(cleaned), len(test_dict) - 2)
        self.assertNotIn(bad_date1, cleaned)
        self.assertNotIn(bad_date2, cleaned)

    def test_hilos_with_missing_data(self):
        # With seven hours of missing observed data, make sure all highs and lows are still found.
        timeline = GraphTimeline(date(2025, 12, 4), date(2025, 12, 5), self.tzone)

        # Get astro predictions for the timeline
        raw = util.read_file(f"{test_data_path}/data/astro-hilo-120405.json")
        contents = astro.extract_json(raw)
        preds_dict = astro.hilo_json_to_dict(station, contents, timeline)

        # Get observed tides from CDMO for the timeline
        with open(f"{test_data_path}/data/cdmo-120405.xml", "r") as file:
            xml = file.read()
        converter = cdmo.make_navd88_level_converter(station.navd88_meters_to_mllw_feet)
        obs_dict = cdmo.parse_cdmo_xml(timeline, xml, "Level", converter)

        # Find the hilos in the observed data.
        hilos = cdmo.find_all_hilos(timeline, obs_dict, preds_dict)
        self.assertEqual(len(hilos), len(preds_dict))
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
                self.assertEqual(val.value, preds_dict[dt].value)

    def test_cdmo_invalid_ip(self):
        xml = self.load_xml("cdmo-invalid-ip.xml")
        timeline = GraphTimeline(date(2025, 3, 31), date(2025, 3, 31), self.tzone)
        with self.assertRaisesRegex(APIException, "^Invalid ip"):
            cdmo.parse_cdmo_xml(timeline, xml, "anyparam", None)

    def test_handle_navd88(self):
        converter = cdmo.make_navd88_level_converter(station.navd88_meters_to_mllw_feet)
        self.assertTrue(converter(None, None) is None)
        self.assertTrue(cdmo.handle_windspeed("nONE", None) is None)
        self.assertTrue(converter("", None) is None)
        self.assertTrue(converter("13s", None) is None)
        self.assertTrue(converter("\n\t", None) is None)

        max_meters = station.mllw_feet_to_navd88_meters(cdmo.max_tide)
        min_meters = station.mllw_feet_to_navd88_meters(cdmo.min_tide)
        self.assertTrue(converter(f"{max_meters + 1.0}", None) is None)
        self.assertTrue(converter(f"{max_meters - 1.0}", None) is not None)
        self.assertTrue(converter(f"{min_meters - 1.0}", None) is None)
        self.assertTrue(converter(f"{min_meters + 1.0}", None) is not None)
        self.assertEqual(
            converter("1.5", None),
            station.navd88_meters_to_mllw_feet(1.5),
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
