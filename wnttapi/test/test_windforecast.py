import json
import os.path
from datetime import date, datetime
from unittest import TestCase

import app.datasource.windforecast as wind
import app.tzutil as tz
import app.util as util
from app.timeline import GraphTimeline

cur_path = os.path.dirname(os.path.abspath(__file__))


class TestWindForecast(TestCase):
    def test_forecast(self):
        """Able to extract forecast data for the future part of a single day."""
        zone = tz.eastern
        now = datetime(2026, 2, 2, 11, 59, tzinfo=zone)

        start = date(2026, 2, 2)
        end = date(2026, 2, 2)
        tline = GraphTimeline(start, end, zone)
        forecast_window = wind.get_forecast_window(tline, now)

        raw = util.read_file(f"{cur_path}/data/wind-20260202-03.json")
        contents = json.loads(raw)["hourly"]

        result = wind.pred_json_to_dict(contents, tline, forecast_window, now)
        self.assertEqual(len(result), 13)
        self.assertEqual(len(result), len(forecast_window))
        self.assertEqual(
            result[min(result)],
            {
                "mph": util.kilometers_to_miles(10.5),
                "dir": 311,
                "dir_str": util.degrees_to_dir(311),
            },
        )
        self.assertEqual(max(result), datetime(2026, 2, 3, 0, tzinfo=zone))
        self.assertEqual(
            result[max(result)],
            {
                "mph": util.kilometers_to_miles(8.1),
                "dir": 302,
                "dir_str": util.degrees_to_dir(302),
            },
        )
