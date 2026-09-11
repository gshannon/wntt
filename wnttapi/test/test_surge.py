# ruff: noqa: I001
import test._bootstrap as boot

from datetime import date, datetime, timedelta
from unittest import TestCase
from zoneinfo import ZoneInfo

import app.station as stn
from app import swmp
from app.datasource import surge
from app.timeline import Timeline

dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestSurge(TestCase):
    wells: stn.Station
    tzone: ZoneInfo

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.wells = boot.load_station("welinwq")
        cls.tzone = cls.wells.time_zone  # Do not change, tests use hard-coded times

    def test_get_surge_file_info(self):

        fileinfo = surge.get_latest_file_info(
            self.wells.noaa_station_id, f"{boot.test_data_dir}"
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
            timeline, self.wells.noaa_station_id, f"{boot.test_data_dir}"
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
