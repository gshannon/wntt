from datetime import datetime
from unittest import TestCase

import app.tzutil as tz
import app.util as util


class TestUtil(TestCase):
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
