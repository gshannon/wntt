from datetime import date, datetime, time
from unittest import TestCase

import app.tzutil as tz

spring_date = date(2024, 3, 10)
fall_date = date(2024, 11, 3)


class TestTzUtil(TestCase):
    def test_is_dst(self):
        standard = datetime(2025, 2, 1, tzinfo=tz.eastern)
        self.assertFalse(tz.is_dst(standard))
        self.assertFalse(
            tz.is_dst(datetime.combine(spring_date, time(), tzinfo=tz.eastern))
        )

        daylight = datetime(2025, 6, 1, tzinfo=tz.central)
        self.assertTrue(tz.is_dst(daylight))
        self.assertTrue(
            tz.is_dst(datetime.combine(fall_date, time(), tzinfo=tz.central))
        )
