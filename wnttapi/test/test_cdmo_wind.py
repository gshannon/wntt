import os.path
from datetime import date, datetime
from unittest import TestCase

import app.datasource.cdmo as cdmo
import app.station as stn
import app.tzutil as tz
from app.timeline import GraphTimeline
from django import setup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

cur_path = os.path.dirname(os.path.abspath(__file__))

wells = stn.get_station("welinwq", f"{cur_path}/../../datamount/stations")
test_data_path = os.path.dirname(os.path.abspath(__file__))
tzone = tz.eastern


class TestCdmo(TestCase):
    def test_parse_windspeed_xml(self):
        start_date = date(2025, 12, 28)
        end_date = date(2025, 12, 28)
        timeline = GraphTimeline(start_date, end_date, tzone)

        with open(f"{test_data_path}/data/cdmo-20251228-wspd.xml", "r") as file:
            xml = file.read()

        wspd_dict = cdmo.parse_cdmo_xml(timeline, wells, xml, [cdmo.Param.WindSpeed])
        with open(f"{test_data_path}/data/cdmo-20251228-maxwspd.xml", "r") as file:
            xml = file.read()

        maxwspd_dict = cdmo.parse_cdmo_xml(timeline, wells, xml, [cdmo.Param.WindGust])

        with open(f"{test_data_path}/data/cdmo-20251228-wdir.xml", "r") as file:
            xml = file.read()

        wdir_dict = cdmo.parse_cdmo_xml(timeline, wells, xml, [cdmo.Param.WindDir])

        # Every data point should be present except for the missing gust at 00:15 on 12/28.
        # This should result in no wind data at all for that time.

        all_wind = wspd_dict | maxwspd_dict | wdir_dict
        wind_data = cdmo.assemble_wind_data(all_wind)
        # 96 data points: (24 hours * 4 per hour) + (1 for 00:00 on 12/29) - (1 for 00:15 on 12/28)
        self.assertEqual(len(wind_data), 96)
        self.assertNotIn(datetime(2025, 12, 27, 23, 45, tzinfo=tzone), wind_data)
        self.assertNotIn(datetime(2025, 12, 28, 0, 15, tzinfo=tzone), wind_data)
        self.assertNotIn(datetime(2025, 12, 29, 0, 15, tzinfo=tzone), wind_data)

        dt = min(wind_data)
        self.assertEqual(dt, datetime(2025, 12, 28, 0, 0, tzinfo=tzone))
        node = wind_data[dt]
        self.assertEqual(node["speed"], 2.9)
        self.assertEqual(node["gust"], 5.6)
        self.assertEqual(node["dir"], 304)
        self.assertEqual(node["dir_str"], "NW")

        dt = max(wind_data)
        self.assertEqual(dt, datetime(2025, 12, 29, 0, 0, tzinfo=tzone))
        node = wind_data[dt]
        self.assertEqual(node["speed"], 2.0)
        self.assertEqual(node["gust"], 3.1)
        self.assertEqual(node["dir"], 255)
        self.assertEqual(node["dir_str"], "WSW")
