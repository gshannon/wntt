# ruff: noqa: I001
import test._bootstrap as boot

import json
from datetime import datetime
from unittest import TestCase

import app.datasource.windforecast as wind
import app.tzutil as tz
from app import util


class TestWindForecast(TestCase):
    def test_uncached_forecast(self):
        """Able to extract forecast data."""
        zone = tz.eastern

        raw = util.read_file(f"{boot.test_data_dir}/wind-20260202-03.json")
        contents = wind.RawForecast.model_validate(json.loads(raw)["hourly"])

        result = wind.pred_json_to_dict(contents, zone)
        self.assertEqual(len(result), 48)
        self.assertEqual(
            result[min(result)],
            {
                "mph": util.kilometers_to_miles(21.5),
                "dir": 325,
            },
        )
        self.assertEqual(max(result), datetime(2026, 2, 3, 23, tzinfo=zone))
        self.assertEqual(
            result[max(result)],
            {
                "mph": util.kilometers_to_miles(12.6),
                "dir": 243,
            },
        )
