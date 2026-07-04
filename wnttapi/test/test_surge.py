import os.path
from datetime import date, datetime, timedelta
from unittest import TestCase

from django import setup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

import app.station as stn
from app import swmp as swmp
from app.datasource import surge
from app.timeline import Timeline

cur_path = os.path.dirname(os.path.abspath(__file__))

wells = stn.get_station("welinwq", f"{cur_path}/../../datamount/stations")
tzone = wells.time_zone  # Do not change, tests use hard-coded times
test_dir_path = os.path.dirname(os.path.abspath(__file__))
dst_start_date = date(2024, 3, 10)
dst_end_date = date(2024, 11, 3)


class TestSurge(TestCase):
    def test_get_surge_file_info(self):

        filepath, filedate, cycle, file_creation_dt = surge.get_latest_file_info(
            wells.noaa_station_id, f"{test_dir_path}/data"
        )

        self.assertTrue(filepath is not None)
        self.assertEqual(filedate, "20260703")
        self.assertEqual(cycle, 0)
        self.assertIsNotNone(file_creation_dt)

    def test_read_surge_file(self):

        start_dt = datetime(2026, 6, 30, 12, tzinfo=tzone)
        end_dt = start_dt + timedelta(hours=4)
        timeline = Timeline(start_dt, end_dt, datetime(2026, 6, 29, tzinfo=tzone))

        data = surge.get_future_surge_data(
            timeline, wells.noaa_station_id, None, f"{test_dir_path}/data"
        )
        self.assertTrue(data is not None)

        # matches the value at start of the hour
        next_tide_dt = datetime(2026, 6, 30, 13, 29, tzinfo=tzone)
        surge_feet = swmp.find_nearest_surge_value(data, next_tide_dt)
        self.assertEqual(surge_feet, 0.3)

        # matches the value at start of the next hour
        next_tide_dt = datetime(2026, 6, 30, 13, 31, tzinfo=tzone)
        surge_feet = swmp.find_nearest_surge_value(data, next_tide_dt)
        self.assertEqual(surge_feet, 0.4)
