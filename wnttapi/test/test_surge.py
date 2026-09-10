import test._bootstrap  # noqa: F401  (configures Django; must precede app.* imports)

import os.path
from datetime import date, datetime, timedelta
from unittest import TestCase
from zoneinfo import ZoneInfo

import app.station as stn
from app import swmp as swmp
from app.datasource import surge
from app.timeline import Timeline

cur_path = os.path.dirname(os.path.abspath(__file__))
test_dir_path = os.path.dirname(os.path.abspath(__file__))
dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestSurge(TestCase):
    wells: stn.Station
    tzone: ZoneInfo

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wells = stn.get_station("welinwq", f"{cur_path}/../../datamount/stations")
        cls.tzone = cls.wells.time_zone  # Do not change, tests use hard-coded times

    def test_get_surge_file_info(self):

        fileinfo = surge.get_latest_file_info(
            self.wells.noaa_station_id, f"{test_dir_path}/data"
        )

        self.assertTrue(fileinfo is not None)
        if fileinfo is not None:
            self.assertEqual(fileinfo.filedate, "20260703")
            self.assertEqual(fileinfo.cycle, 0)
            self.assertIsNotNone(fileinfo.created_at)

    def test_read_surge_file(self):

        start_dt = datetime(2026, 6, 30, 12, tzinfo=self.tzone)
        end_dt = start_dt + timedelta(hours=4)
        timeline = Timeline(start_dt, end_dt, datetime(2026, 6, 29, tzinfo=self.tzone))

        data = surge.get_future_surge_data(
            timeline, self.wells.noaa_station_id, f"{test_dir_path}/data"
        )
        self.assertTrue(data is not None)

        # matches the value at start of the hour
        next_tide_dt = datetime(2026, 6, 30, 13, 29, tzinfo=self.tzone)
        surge_feet = swmp.find_nearest_surge_value(data, next_tide_dt)
        self.assertEqual(surge_feet, 0.3)

        # matches the value at start of the next hour
        next_tide_dt = datetime(2026, 6, 30, 13, 31, tzinfo=self.tzone)
        surge_feet = swmp.find_nearest_surge_value(data, next_tide_dt)
        self.assertEqual(surge_feet, 0.4)
