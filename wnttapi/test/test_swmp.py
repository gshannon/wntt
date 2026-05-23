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


class TestSwmp(TestCase):
    def test_read_surge_file(self):

        start_dt = datetime(2026, 6, 9, 8, tzinfo=tzone)
        end_dt = start_dt + timedelta(days=1)
        timeline = Timeline(start_dt, end_dt, datetime(2026, 6, 9, 8, tzinfo=tzone))

        data = surge.get_future_surge_data(
            timeline, wells.noaa_station_id, None, f"{test_dir_path}/data"
        )
        self.assertTrue(data is not None)

        next_low_tide_dt = datetime(2026, 6, 9, 12, 14, tzinfo=tzone)
        surge_str, dt = swmp.get_surge_info(data, next_low_tide_dt)

        self.assertEqual(surge_str, "0.10")

        next_low_tide_dt = datetime(2026, 6, 9, 8, 55, tzinfo=tzone)
        surge_str, dt = swmp.get_surge_info(data, next_low_tide_dt)

        self.assertEqual(surge_str, "0.30")
