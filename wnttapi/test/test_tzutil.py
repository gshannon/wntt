from unittest import TestCase
from datetime import datetime, date, timedelta
import app.tzutil as tz


class TestTzUtil(TestCase):

    def test_naive_utc5(self):
        """UTC5 is my term for CDMO times that have no time zone, but are always UTC minus 5 hours."""

        spring_date = date(2024,3,10)
        fall_date = date(2024,11,3)

        # Test a standard time, 1 hour before the clocks spring forward.
        naive_utc5 = datetime(spring_date.year, spring_date.month, spring_date.day, 1)
        # We expect this to be 5 hours behind UTC
        expected_utc = tz.utc.localize(datetime(spring_date.year, spring_date.month, spring_date.day, 6))
        self.assertEqual(tz.naive_utc5_to_utc(naive_utc5), expected_utc)
        # And back to Eastern standard time.
        dt = expected_utc.astimezone(tz.eastern)
        expected_dt = tz.eastern.localize(datetime(dt.year, dt.month, dt.day, 1))
        self.assertEqual(expected_utc.astimezone(tz.eastern), expected_dt)

        # Test a daylight time, just after the jump.
        naive_utc5 = datetime(spring_date.year, spring_date.month, spring_date.day, 3)
        # Again, utc5 is 5 hours behind UTC
        expected_utc = tz.utc.localize(datetime(spring_date.year, spring_date.month, spring_date.day, 8))
        self.assertEqual(tz.naive_utc5_to_utc(naive_utc5), expected_utc)
        dt = expected_utc.astimezone(tz.eastern)
        # This time we wind up at 0400, correctly 1 hour past the UTC-5 time.
        expected_dt = tz.eastern.localize(datetime(dt.year, dt.month, dt.day, 4))
        self.assertEqual(expected_utc.astimezone(tz.eastern), expected_dt)

