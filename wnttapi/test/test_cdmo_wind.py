import os.path
from datetime import date, datetime
from unittest import TestCase

import app.datasource.cdmo as cdmo
import app.station as stn
import app.tzutil as tz
import app.util as util
from app.timeline import GraphTimeline
from django import setup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

cur_path = os.path.dirname(os.path.abspath(__file__))

wells = stn.get_station("welinwq", f"{cur_path}/../../datamount/stations")
test_data_path = os.path.dirname(os.path.abspath(__file__))
tzone = tz.eastern


class TestCdmo(TestCase):
    def test_parse_wind_xml(self):
        start_date = date(2025, 12, 28)
        end_date = date(2025, 12, 28)
        timeline = GraphTimeline(start_date, end_date, tzone)

        with open(f"{test_data_path}/data/cdmo-20251228-wind.xml", "r") as file:
            xml = file.read()

        wind_data = cdmo.parse_cdmo_xml(timeline, wells, xml, cdmo.WIND_PARAMS)

        # Every data point should be present except for the missing gust at 00:15 on 12/28.
        # This should result in no wind data at all for that time.

        # 96 data points: (24 hours * 4 per hour) + (1 for 00:00 on 12/29) - (1 for 00:15 on 12/28)
        self.assertEqual(len(wind_data), 96)
        self.assertNotIn(datetime(2025, 12, 27, 23, 45, tzinfo=tzone), wind_data)
        self.assertNotIn(datetime(2025, 12, 28, 0, 15, tzinfo=tzone), wind_data)
        self.assertNotIn(datetime(2025, 12, 29, 0, 15, tzinfo=tzone), wind_data)

        dt = min(wind_data)
        self.assertEqual(dt, datetime(2025, 12, 28, 0, 0, tzinfo=tzone))
        entry = wind_data[dt]
        self.assertEqual(
            entry[cdmo.Param.WindSpeed.label], util.meters_per_second_to_mph(1.7)
        )
        self.assertEqual(
            entry[cdmo.Param.WindGust.label], util.meters_per_second_to_mph(2.8)
        )
        self.assertEqual(entry[cdmo.Param.WindDir.label], 319)

        dt = max(wind_data)
        self.assertEqual(dt, datetime(2025, 12, 29, 0, 0, tzinfo=tzone))
        entry = wind_data[dt]
        self.assertEqual(
            entry[cdmo.Param.WindSpeed.label], util.meters_per_second_to_mph(1.0)
        )
        self.assertEqual(
            entry[cdmo.Param.WindGust.label], util.meters_per_second_to_mph(2.1)
        )
        self.assertEqual(entry[cdmo.Param.WindDir.label], 240)
