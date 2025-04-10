from unittest import TestCase
from datetime import datetime, date, timedelta
import app.datasource.cdmo as cdmo
import app.tzutil as tz
import app.util as util
# import app.graphutil as gu

dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestCdmo(TestCase):

    def test_calculate_hilos(self):
        # Test with a simple dataset
        datadict = {
            date(2024, 1, 1): 1.0,
            date(2024, 1, 2): 2.0,
            date(2024, 1, 3): 3.0,
            date(2024, 1, 4): 2.5,
            date(2024, 1, 5): 2.5,
            date(2024, 1, 6): 3.5,
        }
        expected_hilos = {
            date(2024, 1, 3): 'H',
            date(2024, 1, 4): 'L',
        }
        self.assertEqual(cdmo.find_hilos(datadict), expected_hilos)

    def test_handle_navd88(self):
        self.assertTrue(cdmo.handle_navd88_level(None,None) is None)
        self.assertTrue(cdmo.handle_windspeed('nONE',None) is None)
        self.assertTrue(cdmo.handle_navd88_level('',None) is None)
        self.assertTrue(cdmo.handle_navd88_level('13s',None) is None)
        self.assertTrue(cdmo.handle_navd88_level('\n\t',None) is None)

        max_meters = util.mllw_feet_to_navd88_meters(cdmo.max_tide)
        min_meters = util.mllw_feet_to_navd88_meters(cdmo.min_tide)        
        self.assertTrue(cdmo.handle_navd88_level(f"{max_meters + 1.0}",None) is None)
        self.assertTrue(cdmo.handle_navd88_level(f"{max_meters - 1.0}",None) is not None)
        self.assertTrue(cdmo.handle_navd88_level(f"{min_meters - 1.0}",None) is None)
        self.assertTrue(cdmo.handle_navd88_level(f"{min_meters + 1.0}",None) is not None)
        self.assertEqual(cdmo.handle_navd88_level('1.5', None), util.navd88_meters_to_mllw_feet(1.5))


    def test_handle_windspeed(self):
        self.assertTrue(cdmo.handle_windspeed(None,None) is None)
        self.assertTrue(cdmo.handle_windspeed('nONe',None) is None)
        self.assertTrue(cdmo.handle_windspeed('',None) is None)
        self.assertTrue(cdmo.handle_windspeed('7..3',None) is None)
        self.assertTrue(cdmo.handle_windspeed('\n\t',None) is None)
        self.assertTrue(cdmo.handle_windspeed('-0.5',None) is None)
        self.assertTrue(cdmo.handle_windspeed('121.0',None) is None)
        self.assertEqual(cdmo.handle_windspeed('13.3',None), util.meters_per_second_to_mph(13.3))

    def test_cdmo_dates_standard(self):
        """In standard time, with non-padded timeline, no changes are needed for any time zone."""
        # January is in Standard time
        start_date = date(2024, 1, 10)
        end_date = date(2024, 1, 12)
        for tzone in [tz.central, tz.mountain, tz.pacific]:
            timeline = util.build_timeline(start_date, end_date, tzone, padded=False)
            self.assertEqual(cdmo.compute_cdmo_request_dates(timeline), (start_date, end_date))

        """In standard time, with normal padded timeline, end date is moved forward 1 day."""
        start_date = date(2024, 1, 10)
        end_date = date(2024, 1, 12)
        expected_end_date = end_date + timedelta(days=1)
        for tzone in [tz.central, tz.mountain, tz.pacific]:
            timeline = util.build_timeline(start_date, end_date, tzone, padded=True)
            self.assertEqual(cdmo.compute_cdmo_request_dates(timeline), (start_date, expected_end_date))

 
    def test_cdmo_dates_daylight_savings_for_graph(self):
        """In DST, if first datetime is at midnight, start date is moved back one day regardless of padding or zone."""
        # July is in DST
        start_date = date(2024, 7, 10)
        end_date = date(2024, 7, 10)
        expected_start_date = start_date - timedelta(days=1)
        for tzone in [tz.central, tz.mountain, tz.pacific]:
            timeline = util.build_timeline(start_date, end_date, tzone, padded=False)
            self.assertEqual(cdmo.compute_cdmo_request_dates(timeline), (expected_start_date, end_date))
            timeline = util.build_timeline(start_date, end_date, tzone, padded=True)
            self.assertEqual(cdmo.compute_cdmo_request_dates(timeline), (expected_start_date, end_date))


    def test_cdmo_dates_daylight_savings_for_recent(self):
        """In DST, for getting recent data, if first datetime is not midnight, dates are computed correctly."""
        # July is in DST
        start_dt = datetime(2024, 7, 10, 1, 0, tzinfo=tz.eastern)
        end_dt = datetime(2024, 7, 10, 4, 0, tzinfo=tz.eastern)
        timeline = util.build_recent_data_timeline(start_dt, end_dt)
        self.assertEqual(cdmo.compute_cdmo_request_dates(timeline), (start_dt.date(), start_dt.date()))

        start_dt = datetime(2024, 7, 10, 0, 0, tzinfo=tz.eastern)
        end_dt = datetime(2024, 7, 10, 23, 45, tzinfo=tz.eastern)
        timeline = util.build_recent_data_timeline(start_dt, end_dt)
        expected_start_date = start_dt.date() - timedelta(days=1)
        self.assertEqual(cdmo.compute_cdmo_request_dates(timeline), (expected_start_date, start_dt.date()))
