import os.path
from datetime import date, datetime
from unittest import TestCase

import app.datasource.cdmo as cdmo
import app.tzutil as tz
from app.timeline import GraphTimeline

test_data_path = os.path.dirname(os.path.abspath(__file__))
tzone = tz.eastern


class TestCdmo(TestCase):
    def test_parse_windspeed_xml(self):
        start_date = date(2025, 12, 28)
        end_date = date(2025, 12, 28)
        timeline = GraphTimeline(start_date, end_date, tzone)

        with open(f"{test_data_path}/data/cdmo-20251228-wspd.xml", "r") as file:
            xml = file.read()

        wspd_dict = cdmo.parse_cdmo_xml(
            timeline, xml, cdmo.windspeed_param, cdmo.handle_windspeed
        )

        with open(f"{test_data_path}/data/cdmo-20251228-maxwspd.xml", "r") as file:
            xml = file.read()

        maxwspd_dict = cdmo.parse_cdmo_xml(
            timeline, xml, cdmo.windgust_param, cdmo.handle_windspeed
        )

        with open(f"{test_data_path}/data/cdmo-20251228-wdir.xml", "r") as file:
            xml = file.read()

        wdir_dict = cdmo.parse_cdmo_xml(
            timeline, xml, cdmo.winddir_param, lambda d, dt: int(d)
        )

        # Every data point should be present except for the missing gust at 00:15 on 12/28.
        # This should result in no wind data at all for that time.

        wind_data = cdmo.assemble_wind_data(wspd_dict, maxwspd_dict, wdir_dict)
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
