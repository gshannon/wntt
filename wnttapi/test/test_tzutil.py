from unittest import TestCase
from datetime import datetime, date, time
import app.tzutil as tz

spring_date = date(2024,3,10)
fall_date = date(2024,11,3)

class TestTzUtil(TestCase):

    def test_is_dst(self):

        naive = datetime(2024, 3, 10, 1, 0)
        self.assertRaises(ValueError, tz.isDst, naive)

        standard = datetime(2025, 2, 1, tzinfo=tz.eastern)
        self.assertFalse(tz.isDst(standard))
        self.assertFalse(tz.isDst(datetime.combine(spring_date, time(), tzinfo=tz.eastern)))

        daylight = datetime(2025, 6, 1, tzinfo=tz.central)
        self.assertTrue(tz.isDst(daylight))
        self.assertTrue(tz.isDst(datetime.combine(fall_date, time(), tzinfo=tz.central)))
