from unittest import TestCase
from datetime import datetime, date, timedelta
import app.util as util
import app.tzutil as tz
from rest_framework.exceptions import APIException


class TestGraphUtil(TestCase):

    def test_build_timeline(self):
        normal_count = 97   # Timeline that doesn't cross a DST boundary contains 97 elements.
        start_date = end_date = date(2024, 3, 1)
        timeline = util.build_timeline(start_date, end_date, tz.eastern)
        self.assertEqual(len(timeline), normal_count)
        self.assertEqual(timeline[0], tz.eastern.localize(datetime(2024, 3, 1, 0)))
        self.assertEqual(timeline[normal_count-1], tz.eastern.localize(datetime(2024, 3, 2, 0)))

        # Start of DST, skips 2AM (4 elements)
        start_date = end_date = date(2024, 3, 10)
        timeline = util.build_timeline(start_date, end_date, tz.eastern)
        self.assertEqual(len(timeline), normal_count - 4)

        # End of DST, repeats 1AM (should have 4 extra elements)
        start_date = end_date = date(2024, 11, 3)
        timeline = util.build_timeline(start_date, end_date, tz.eastern)
        self.assertEqual(len(timeline), normal_count + 4)

        # Skipping the extra time at the end
        start_date = date(2023, 12, 30)
        end_date = start_date + timedelta(days=9)
        timeline = util.build_timeline(start_date, end_date, tz.pacific, extra=False)
        self.assertEqual(len(timeline), ((normal_count - 1) * 10))

        bad_time_count = 0
        for dt in timeline:
            if dt.minute not in (0, 15, 30, 45):
                bad_time_count += 1
        self.assertEqual(bad_time_count, 0)

        start_date = date(2024, 3, 1)
        end_date = date(2024, 2, 28)
        self.assertRaises(APIException, util.build_timeline, start_date, end_date, tz.eastern)

    def test_dt_rounding(self):
        dt = datetime(2023, 12, 31, 23, 0, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), dt)
        dt = datetime(2023, 12, 31, 23, 7, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 0, tzinfo=tz.eastern))
        dt = datetime(2023, 12, 31, 23, 17, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 15, tzinfo=tz.eastern))
        dt = datetime(2023, 12, 31, 23, 18, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 15, tzinfo=tz.eastern))
        dt = datetime(2023, 12, 31, 23, 52, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), datetime(2023, 12, 31, 23, 45, tzinfo=tz.eastern))
        dt = datetime(2023, 12, 31, 23, 53, tzinfo=tz.eastern)
        self.assertEqual(util.round_to_quarter(dt), datetime(2024, 1, 1, 0, 0, tzinfo=tz.eastern))


    def test_timeline_info(self):
        start_date = end_date = date(2024, 6, 1)
        timeline = util.build_timeline(start_date, end_date, tz.eastern)
        tzone = timeline[0].tzinfo

        # All in the future
        (a, b) = util.get_timeline_info(timeline, tzone.localize(datetime(2024,6,1)))
        self.assertEqual((a,b), (-1, -1))

        # All in the past.
        (a, b) = util.get_timeline_info(timeline, tzone.localize(datetime(2024,6,2)))
        self.assertEqual((a,b), (0,-1))

        # Mixed
        (a, b) = util.get_timeline_info(timeline,
            tzone.localize(datetime(2024,6,1, 0, 1)))
        self.assertEqual((a,b), (0, 1))

        (a, b) = util.get_timeline_info(timeline,
            tzone.localize(datetime(2024,6,1, 23, 59)))
        self.assertEqual((a,b), (0, 96))
