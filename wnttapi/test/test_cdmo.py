from unittest import TestCase
from datetime import date, timedelta
import app.datasource.cdmo as cdmo
import app.tzutil as tz
import app.util as util

dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestCdmo(TestCase):
    def setUp(self):
        pass

    def test_handle_navd88(self):
        self.assertTrue(cdmo.handle_navd88_level(None) is None)
        self.assertTrue(cdmo.handle_windspeed('nONE') is None)
        self.assertTrue(cdmo.handle_navd88_level('') is None)
        self.assertTrue(cdmo.handle_navd88_level('13s') is None)
        self.assertTrue(cdmo.handle_navd88_level('\n\t') is None)
        self.assertTrue(cdmo.handle_navd88_level('21.0') is None)
        self.assertTrue(cdmo.handle_navd88_level('-21.0') is None)
        self.assertEqual(cdmo.handle_navd88_level('11.5'), util.meters_navd88_to_feet_mllw(11.5))
        self.assertEqual(cdmo.handle_navd88_level('0'), util.meters_navd88_to_feet_mllw(0))

    def test_handle_windspeed(self):
        self.assertTrue(cdmo.handle_windspeed(None) is None)
        self.assertTrue(cdmo.handle_windspeed('nONe') is None)
        self.assertTrue(cdmo.handle_windspeed('') is None)
        self.assertTrue(cdmo.handle_windspeed('7..3') is None)
        self.assertTrue(cdmo.handle_windspeed('\n\t') is None)
        self.assertTrue(cdmo.handle_windspeed('-0.5') is None)
        self.assertTrue(cdmo.handle_windspeed('121.0') is None)
        self.assertEqual(cdmo.handle_windspeed('13.3'), util.meters_per_second_to_mph(13.3))

    def test_cdmo_dates_standard(self):
        """In standard time, all US time zones except Eastern are > 5 hours behind, so end date must be adjusted"""
        start_date = date(2024,1,10)
        end_date = date(2024, 1, 17)
        expected_end_date = end_date + timedelta(days=1)
        for tzone in [tz.central, tz.mountain, tz.pacific]:
            self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tzone), (start_date, expected_end_date))

        """For US/Eastern, starting any day before DST starts should require no changes, and it doesn't matter
        whether the end date is in DST or not."""
        tzone = tz.eastern
        start_date = dst_start_date - timedelta(days=1)  # day before DST starts
        end_date = start_date
        self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tzone), (start_date, end_date))
        end_date = dst_start_date
        self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tzone), (start_date, end_date))
        end_date = dst_start_date + timedelta(days=3)
        self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tzone), (start_date, end_date))

    def test_cdmo_dates_eastern_daylight(self):
        start_date = date(2024, 6, 1)
        end_date = start_date
        adjustted_start_date = start_date - timedelta(days=1)

        # For US/Eastern, any start day during DST requires an earlier start date or else will miss the 1st hour.
        self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tz.eastern),
                         (adjustted_start_date, end_date))

        # For Central, any start day during DST requires no changes since it is UTC - 5, matching CDMO exactly.
        self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tz.central),
                         (start_date, end_date))

        # For other zones, start_date needs no change because they are 5+ hours behind UTC.
        adjusted_end_date = end_date + timedelta(days=1)
        for tzone in [tz.mountain, tz.pacific]:
            self.assertEqual(cdmo.compute_cdmo_request_dates(start_date, end_date, tzone),
                             (start_date, adjusted_end_date))
