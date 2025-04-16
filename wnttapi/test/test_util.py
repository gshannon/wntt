from datetime import date, datetime
from unittest import TestCase

import app.tzutil as tz
import app.util as util


class TestGraphUtil(TestCase):
    def test_build_timeline(self):
        normal_count = (
            96  # Timeline that doesn't cross a DST boundary contains 96 elements.
        )
        start_date = end_date = date(2024, 3, 1)
        timeline = util.build_timeline(start_date, end_date, tz.eastern, padded=False)
        self.assertEqual(len(timeline), normal_count)
        self.assertEqual(timeline[0], datetime(2024, 3, 1, 0, tzinfo=tz.eastern))
        self.assertEqual(timeline[-1], datetime(2024, 3, 1, 23, 45, tzinfo=tz.eastern))

        # Start of DST, skips 2AM (4 elements)
        start_date = end_date = date(2024, 3, 10)
        timeline = util.build_timeline(start_date, end_date, tz.eastern, padded=False)
        self.assertEqual(len(timeline), normal_count - 4)

        # End of DST, repeats 1AM (should have 4 extra elements)
        start_date = end_date = date(2024, 11, 3)
        timeline = util.build_timeline(start_date, end_date, tz.eastern, padded=False)
        self.assertEqual(len(timeline), normal_count + 4)

        bad_time_count = 0
        for dt in timeline:
            if dt.minute not in (0, 15, 30, 45):
                bad_time_count += 1
        self.assertEqual(bad_time_count, 0)

        start_date = date(2024, 3, 1)
        end_date = date(2024, 2, 28)
        self.assertRaises(
            Exception, util.build_timeline, start_date, end_date, tz.eastern
        )

    def test_dt_rounding(self):
        dt = datetime(2023, 12, 31, 23, 0, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), dt)
        dt = datetime(2023, 12, 31, 23, 7, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 0, tzinfo=tz.eastern)
        )
        dt = datetime(2023, 12, 31, 23, 17, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 15, tzinfo=tz.eastern)
        )
        dt = datetime(2023, 12, 31, 23, 18, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 15, tzinfo=tz.eastern)
        )
        dt = datetime(2023, 12, 31, 23, 52, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 45, tzinfo=tz.eastern)
        )
        dt = datetime(2023, 12, 31, 23, 53, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_to_quarter(dt), datetime(2024, 1, 1, tzinfo=tz.eastern)
        )

        dt = datetime(2023, 12, 31, 22, 45, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_up_to_quarter(dt),
            datetime(2023, 12, 31, 23, 0, tzinfo=tz.eastern),
        )
        dt = datetime(2023, 12, 31, 23, 0, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_up_to_quarter(dt),
            datetime(2023, 12, 31, 23, 15, tzinfo=tz.eastern),
        )
        dt = datetime(2023, 12, 31, 23, 17, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_up_to_quarter(dt),
            datetime(2023, 12, 31, 23, 30, tzinfo=tz.eastern),
        )
        dt = datetime(2023, 12, 31, 23, 18, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_up_to_quarter(dt),
            datetime(2023, 12, 31, 23, 30, tzinfo=tz.eastern),
        )
        dt = datetime(2023, 12, 31, 23, 52, tzinfo=tz.eastern)
        self.assertEqual(
            util.round_up_to_quarter(dt), datetime(2024, 1, 1, tzinfo=tz.eastern)
        )

    def test_timeline_boundaries(self):
        start_date = end_date = date(2024, 6, 1)
        tzone = tz.eastern
        timeline = util.build_timeline(start_date, end_date, tzone)

        # All in the future
        (a, b) = util.get_timeline_boundaries(
            timeline, datetime(2024, 6, 1, tzinfo=tzone)
        )
        self.assertEqual((a, b), (-1, -1))

        # All in the past.
        (a, b) = util.get_timeline_boundaries(
            timeline, datetime(2024, 6, 2, tzinfo=tzone)
        )
        self.assertEqual((a, b), (0, -1))

        # Mixed
        (a, b) = util.get_timeline_boundaries(
            timeline, datetime(2024, 6, 1, 0, 1, 0, tzinfo=tzone)
        )
        self.assertEqual((a, b), (0, 1))
