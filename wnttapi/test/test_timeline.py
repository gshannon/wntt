from datetime import date, datetime
from unittest import TestCase

import app.graphutil as gu
import app.tzutil as tz
from app.timeline import GraphTimeline, HiloTimeline

spring_date = date(2024, 3, 10)
fall_date = date(2024, 11, 3)


class TestGraphTimeline(TestCase):
    def test_handles_dst(self):
        # GraphTimeline creates correct timeline for days where Daylight Savings Time starts or end.
        zone = tz.eastern

        normal_count = (
            97  # Graph timeline that doesn't cross a DST boundary contains 97 elements.
        )
        start_date = end_date = date(2024, 3, 1)

        timeline = GraphTimeline(start_date, end_date, zone)
        self.assertEqual(len(timeline._raw_times), normal_count)
        self.assertEqual(timeline.start_dt, datetime(2024, 3, 1, 0, tzinfo=zone))
        self.assertEqual(timeline.end_dt, datetime(2024, 3, 2, 0, tzinfo=zone))

        # Start of DST, skips 2AM (4 elements)
        start_date = end_date = spring_date
        timeline = GraphTimeline(start_date, end_date, zone)
        self.assertEqual(timeline.length(), normal_count - 4)

        # End of DST, repeats 1AM (should have 4 extra elements)
        start_date = end_date = fall_date
        timeline = GraphTimeline(start_date, end_date, zone)
        self.assertEqual(timeline.length(), normal_count + 4)
        self.assertEqual(timeline._raw_times[0].day, timeline._raw_times[-2].day)
        self.assertNotEqual(timeline._raw_times[0].day, timeline._raw_times[-1].day)

        bad_time_count = 0
        for dt in timeline._raw_times:
            if dt.minute not in (0, 15, 30, 45):
                bad_time_count += 1
        self.assertEqual(bad_time_count, 0)

    def test_finds_past_dts(self):
        zone = tz.eastern
        start_date = date(2025, 7, 15)
        end_date = date(2025, 7, 16)

        timeline = GraphTimeline(start_date, end_date, zone)
        self.assertEqual(timeline.length(), (96 * 2) + 1)

        timeline.now = datetime(2025, 7, 16, 1, 7, tzinfo=zone)
        past = timeline.get_all_past()
        self.assertEqual(len(past), 96 + 5)  # full day (96) + 1 hour (4) + 01:00 (1)

        # force them all in the future
        timeline.now = datetime(2025, 7, 15, 0, 0, tzinfo=zone)
        past = timeline.get_all_past()
        self.assertEqual(len(past), 0)

        # force all in the past
        timeline.now = datetime(2025, 7, 17, 5, 23, tzinfo=zone)
        past = timeline.get_all_past()
        self.assertEqual(len(past), timeline.length())

    def test_graph_final_times(self):
        # GraphTimeline correctly substitutes corrected times in the timeline
        zone = tz.eastern
        start_date = date(2025, 8, 5)
        end_date = date(2025, 8, 5)
        timeline = GraphTimeline(start_date, end_date, zone)
        original_time_1 = datetime(2025, 8, 5, 7, 45, tzinfo=zone)
        real_time_1 = datetime(2025, 8, 5, 7, 51, tzinfo=zone)
        original_time_2 = datetime(2025, 8, 5, 15, 30, tzinfo=zone)
        real_time_2 = datetime(2025, 8, 5, 15, 26, tzinfo=zone)
        self.assertTrue(original_time_1 in timeline._raw_times)
        self.assertTrue(real_time_1 not in timeline._raw_times)
        self.assertTrue(original_time_2 in timeline._raw_times)
        self.assertTrue(real_time_2 not in timeline._raw_times)

        corrections = {
            original_time_1: {"real_dt": real_time_1},
            original_time_2: {"real_dt": real_time_2},
        }
        final = timeline.get_final_times(corrections)
        self.assertEqual(timeline.length(), len(final))
        self.assertNotEqual(final, timeline._raw_times)
        self.assertTrue(original_time_1 not in final)
        self.assertTrue(real_time_1 in final)
        self.assertTrue(original_time_2 not in final)
        self.assertTrue(real_time_2 in final)

    def test_build_plot(self):
        zone = tz.hawaii
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 1)
        timeline = GraphTimeline(start_date, end_date, zone)

        data = {}
        plot = timeline.build_plot(lambda dt: data.get(dt, None))
        self.assertEqual(timeline.length(), len(plot))
        self.assertEqual(plot, [None] * len(plot))

        data = {datetime(2025, 9, 1, 3, 15, tzinfo=zone): 12.51}
        plot = timeline.build_plot(lambda dt: data.get(dt, None))
        self.assertEqual(timeline.length(), len(plot))
        self.assertTrue(12.51 in plot)


class TestHiloTimeline(TestCase):
    def test_build_wind_plots_hilo(self):
        zone = tz.mountain
        start_date = date(2025, 2, 1)
        end_date = date(2025, 2, 1)
        past_hilo_time_1 = datetime(2025, 2, 1, 2, 15, tzinfo=zone)
        past_hilo_time_2 = datetime(2025, 2, 1, 11, 45, tzinfo=zone)
        later_hilo_time_1 = datetime(2025, 2, 1, 14, 00, tzinfo=zone)
        later_hilo_time_2 = datetime(2025, 2, 1, 23, 30, tzinfo=zone)
        non_hilo_time_1 = datetime(2025, 2, 1, 0, 0, tzinfo=zone)
        non_hilo_time_2 = datetime(2025, 2, 1, 9, 30, tzinfo=zone)

        wind_dict = {
            non_hilo_time_1: {"speed": 8.1, "gust": 22, "dir": 0, "dir_str": "N"},
            non_hilo_time_2: {"speed": 16, "gust": 35.2, "dir": 60, "dir_str": "ENE"},
            past_hilo_time_1: {"speed": 12, "gust": 15.5, "dir": 325, "dir_str": "NW"},
        }

        timeline = HiloTimeline(start_date, end_date, zone)
        timeline.register_hilo_times(
            [past_hilo_time_1, past_hilo_time_2], [later_hilo_time_1, later_hilo_time_2]
        )

        wind_speed_plot, wind_gust_plot, wind_dir_plot, wind_dir_hover = (
            gu.build_wind_plots(timeline, wind_dict)
        )
        self.assertEqual(wind_speed_plot, [None, 12, None, None, None, None])
        self.assertEqual(wind_gust_plot, [None, 15.5, None, None, None, None])
        self.assertEqual(wind_dir_plot, [None, 325, None, None, None, None])
        self.assertEqual(wind_dir_hover, [None, "NW", None, None, None, None])

    def test_hilo_past_with_data(self):
        # HiloTimeline supports storing subset of timeline which must be from the past
        zone = tz.pacific
        start_date = date(2025, 8, 16)
        end_date = date(2025, 8, 20)
        timeline = HiloTimeline(start_date, end_date, zone)
        timeline.now = datetime(2025, 8, 18, 0, 0, tzinfo=zone)
        dt1 = datetime(2025, 8, 16, 0, 15, tzinfo=zone)
        dt2 = datetime(2025, 8, 16, 14, 45, tzinfo=zone)
        dt3 = datetime(2025, 8, 16, 22, 30, tzinfo=zone)
        dt4 = datetime(2025, 8, 19, 4, 0, tzinfo=zone)
        with self.assertRaisesRegex(ValueError, "duplicates"):
            timeline.register_hilo_times([dt1, dt1, dt3], [])
        with self.assertRaisesRegex(ValueError, "duplicates"):
            timeline.register_hilo_times([], [dt4, dt4])

        with self.assertRaisesRegex(ValueError, "must be in past"):
            timeline.register_hilo_times([dt1, dt2, dt3, dt4], [])

        with self.assertRaisesRegex(ValueError, "must be after"):
            timeline.register_hilo_times([dt1, dt2], [dt2, dt4])

    def test_build_hilo_plot(self):
        zone = tz.hawaii
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 1)
        timeline = HiloTimeline(start_date, end_date, zone)
        timeline.now = datetime(2025, 8, 30, 0, 0, tzinfo=zone)

        plot = timeline.build_plot(lambda _: None)
        self.assertEqual(len(plot), 2)
        self.assertEqual(plot, [None] * len(plot))

        data = {datetime(2025, 9, 1, 3, 15, tzinfo=zone): 12.51}
        timeline.register_hilo_times([], list(data.keys()))
        plot = timeline.build_plot(lambda dt: data.get(dt, None))
        self.assertEqual(len(plot), 3)
        self.assertTrue(12.51 in plot)
