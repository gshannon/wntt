from unittest import TestCase
from datetime import datetime, date, timedelta
import app.datasource.cdmo as cdmo
import app.tzutil as tz
import app.util as util

dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestCdmo(TestCase):


    def test_calculate_hilos(self):
        def build_test_data(tides, start_dt = datetime(2025,1,1)):
            timeline = [start_dt + timedelta(minutes=(x*15)) for x in range(0,(len(tides)))]
            d = dict(zip(timeline,tides))  # no None's in datadict
            datadict = {key: val for key, val in d.items() if val is not None} 
            return timeline, datadict

        # Single data value
        tides = [1,1,1,1,1,1,1,1,1,1]
        timeline, _ = build_test_data(tides)
        datadict = {datetime(2025,1,1): 8}
        self.assertEqual(cdmo.find_hilos(timeline, datadict), {})

        # Minimal high only 
        tides = [None, 4, 3, 4, None, 10]
        timeline, datadict = build_test_data(tides)
        expected_hilos = {
            datetime(2025,1,1,0,30): 'L',
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

        # Minimal high only 
        tides = [None, 4, 3, 4, None, 10]
        timeline, datadict = build_test_data(tides)
        expected_hilos = {
            datetime(2025,1,1,0,30): 'L',
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

        # Minimal high and low
        tides = [None, 4, 3, 4, None, 9, 10, 9, None]
        timeline, datadict = build_test_data(tides)
        expected_hilos = {
            datetime(2025,1,1,0,30): 'L',
            datetime(2025,1,1,1,30): 'H',
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)

        # Highs and lows are on the edge, no opposite direction detected
        tides = [3, 4, 5, 6, 7, 8, 9, 10]
        timeline, datadict = build_test_data(tides)
        self.assertEqual(cdmo.find_hilos(timeline, datadict), {})

        # high and low both compromised by None
        tides = [8, 9, 10, 10, None, 9, 8, 7, 5, 4, 3, None, 2, 2, 3, 4]
        timeline, datadict = build_test_data(tides)
        self.assertEqual(cdmo.find_hilos(timeline, datadict), {})

        # actual data from 3/1/2025
        tides = [9.8, 9.62, 9.371, 9.01, 8.58, 8.12, 7.57, 6.975, 6.31, 5.66, 4.975, 4.25, 3.524, 2.78, 2.09,
            1.427, 0.8701, 0.2175, -0.010675, -0.3701, -0.7002, -0.8301, -0.8301, -0.9306, -0.8301, -0.47064, -0.2402,
            0.0886, 0.5801, 1.137, 1.697, 2.286, 2.935, 3.657, 4.31, 5.10, 5.725, 6.44, 7.17, 7.85, 8.42, 8.98,
            9.34, 9.7, 10, 10.29, 10.52, 10.621, 10.68, 10.64, 10.48, 10.26, 9.89, 9.54, 9.14, 8.58, 7.95, 7.27,
            6.52, 5.76, 5.01, 4.29, 3.564, 2.738, 2.016, 1.266, 0.806, 0.185, -0.11032, -0.5, -0.7705, -0.7304, -1.1904,
            -0.7002, -0.7304, -0.47064, -0.11032, 0.1201, 0.677, 1.064, 1.657, 2.32, 2.907, 3.697, 4.29, 4.88, 5.52,
            6.35, 7.03, 7.725, 8.26, 8.71, 9.14, 9.41, 9.7, 9.86, 9.93]
        timeline, datadict = build_test_data(tides, datetime(2025,3,1))
        expected_hilos = {
            datetime(2025,3,1,5,45): 'L',
            datetime(2025,3,1,12,0): 'H',
            datetime(2025,3,1,18,0): 'L',
        }
        self.assertEqual(cdmo.find_hilos(timeline, datadict), expected_hilos)


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
