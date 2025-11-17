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
        self.assertEqual(len(timeline._requested_times), normal_count)
        self.assertEqual(timeline.start_dt, datetime(2024, 3, 1, 0, tzinfo=zone))
        self.assertEqual(timeline.end_dt, datetime(2024, 3, 2, 0, tzinfo=zone))

        # Start of DST, skips 2AM (4 elements)
        start_date = end_date = spring_date
        timeline = GraphTimeline(start_date, end_date, zone)
        self.assertEqual(timeline.length_requested(), normal_count - 4)

        # End of DST, repeats 1AM (should have 4 extra elements)
        start_date = end_date = fall_date
        timeline = GraphTimeline(start_date, end_date, zone)
        self.assertEqual(timeline.length_requested(), normal_count + 4)
        self.assertEqual(
            timeline._requested_times[0].day, timeline._requested_times[-2].day
        )
        self.assertNotEqual(
            timeline._requested_times[0].day, timeline._requested_times[-1].day
        )

        bad_time_count = 0
        for dt in timeline._requested_times:
            if dt.minute not in (0, 15, 30, 45):
                bad_time_count += 1
        self.assertEqual(bad_time_count, 0)

    def test_identifies_past_dts(self):
        zone = tz.eastern
        start_date = date(2025, 7, 15)
        end_date = date(2025, 7, 16)

        # some in past, some in future
        timeline = GraphTimeline(
            start_date, end_date, zone, datetime(2025, 7, 16, 1, 7, tzinfo=zone)
        )
        past = timeline.get_all_past()
        self.assertEqual(
            len(past), 96 + 5 + timeline._padding_points
        )  # full day (96) + 1 hour (4) + 01:00 (1) + pre-timeline padding

        # all in the future
        timeline = GraphTimeline(
            start_date, end_date, zone, datetime(2025, 7, 14, tzinfo=zone)
        )
        past = timeline.get_all_past()
        self.assertEqual(len(past), 0)

        # all in the past
        timeline = GraphTimeline(
            start_date, end_date, zone, datetime(2025, 7, 17, 4, 23, tzinfo=zone)
        )
        past = timeline.get_all_past()
        self.assertEqual(
            len(past), timeline.length_requested() + (timeline._padding_points * 2)
        )

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
        self.assertTrue(original_time_1 in timeline._requested_times)
        self.assertTrue(real_time_1 not in timeline._requested_times)
        self.assertTrue(original_time_2 in timeline._requested_times)
        self.assertTrue(real_time_2 not in timeline._requested_times)

        corrections = {
            original_time_1: real_time_1,
            original_time_2: real_time_2,
        }
        final = timeline.get_final_times(corrections)
        self.assertEqual(timeline.length_requested(), len(final))
        self.assertNotEqual(final, timeline._requested_times)
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
        self.assertEqual(timeline.length_requested(), len(plot))
        self.assertEqual(plot, [None] * len(plot))

        data = {datetime(2025, 9, 1, 3, 15, tzinfo=zone): 12.51}
        plot = timeline.build_plot(lambda dt: data.get(dt, None))
        self.assertEqual(timeline.length_requested(), len(plot))
        self.assertTrue(12.51 in plot)

    def test_add_date_to_timeline(self):
        zone = tz.eastern
        start_date = date(2025, 7, 15)
        end_date = date(2025, 7, 15)

        timeline = GraphTimeline(start_date, end_date, zone)
        len1 = timeline.length_requested()
        adder = datetime(2025, 7, 15, 19, 54, tzinfo=zone)
        timeline.add_time(adder)
        self.assertEqual(timeline.length_requested(), len1 + 1)
        self.assertTrue(timeline.contains(adder))


class TestHiloTimeline(TestCase):
    def test_register_hilo_times_called(self):
        # HiloTimeline.register_hilo_times() must be called before build_plot()
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 1)
        timeline = HiloTimeline(start_date, end_date, tz.central)

        with self.assertRaisesRegex(ValueError, "must be called first"):
            timeline.build_plot(lambda _: None)
        with self.assertRaisesRegex(ValueError, "must be called first"):
            timeline.get_final_times({})

    def test_build_wind_plots_hilo(self):
        zone = tz.mountain
        start_date = date(2025, 2, 1)
        end_date = date(2025, 2, 1)
        past_hilo_time_1 = datetime(2025, 2, 1, 2, 15, tzinfo=zone)
        past_hilo_time_2 = datetime(2025, 2, 1, 11, 45, tzinfo=zone)
        later_hilo_time_1 = datetime(2025, 2, 1, 14, 00, tzinfo=zone)
        later_hilo_time_2 = datetime(2025, 2, 1, 23, 30, tzinfo=zone)
        non_hilo_time_1 = datetime(2025, 2, 1, 0, 15, tzinfo=zone)
        non_hilo_time_2 = datetime(2025, 2, 1, 9, 30, tzinfo=zone)

        wind_dict = {
            non_hilo_time_1: {"speed": 8.1, "gust": 22, "dir": 0, "dir_str": "N"},
            non_hilo_time_2: {"speed": 16, "gust": 35.2, "dir": 60, "dir_str": "ENE"},
            past_hilo_time_1: {"speed": 12, "gust": 15.5, "dir": 325, "dir_str": "NW"},
        }

        timeline = HiloTimeline(start_date, end_date, zone)
        timeline.register_hilo_times(
            [past_hilo_time_1, past_hilo_time_2, later_hilo_time_1, later_hilo_time_2]
        )

        wind_speed_plot, wind_gust_plot, wind_dir_plot, wind_dir_hover = (
            gu.build_wind_plots(timeline, wind_dict)
        )
        self.assertEqual(wind_speed_plot, [None, 12, None, None, None, None])
        self.assertEqual(wind_gust_plot, [None, 15.5, None, None, None, None])
        self.assertEqual(wind_dir_plot, [None, 325, None, None, None, None])
        self.assertEqual(wind_dir_hover, [None, "NW", None, None, None, None])

    def test_hilo_plot_with_boundary_data(self):
        zone = tz.hawaii
        start_date = date(2025, 9, 1)
        end_date = date(2025, 9, 1)
        timeline = HiloTimeline(
            start_date, end_date, zone, datetime(2025, 8, 30, 0, 0, tzinfo=zone)
        )

        dt1 = datetime(2025, 9, 1, 0, tzinfo=zone)
        dt2 = datetime(2025, 9, 1, 3, 15, tzinfo=zone)
        dt3 = datetime(2025, 9, 2, 0, tzinfo=zone)
        data = {dt1: 8.0, dt2: 12.51, dt3: 9.3}
        timeline.register_hilo_times(list(data.keys()))
        plot = timeline.build_plot(lambda dt: data.get(dt, None))
        self.assertEqual(plot, [8.0, 12.51, 9.3])

    def test_add(self):
        zone = tz.eastern
        start_date = date(2025, 7, 15)
        end_date = date(2025, 7, 15)

        timeline = GraphTimeline(start_date, end_date, zone)
        len1 = timeline.length_requested()
        adder = datetime(2025, 7, 15, 19, 54, tzinfo=zone)
        timeline.add_time(adder)
        self.assertEqual(timeline.length_requested(), len1 + 1)
        self.assertTrue(timeline.contains(adder))
