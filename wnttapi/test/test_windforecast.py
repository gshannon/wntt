# ruff: noqa: I001
import test._bootstrap as boot

import json
from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

from django.core.cache import cache

import app.datasource.windforecast as wind
import app.tzutil as tz
from app import util
from app.timeline import GraphTimeline


class TestWindForecast(TestCase):
    def test_pull_data_none_is_handled(self):
        """pull_data's own @util.request_logger swallows request exceptions (e.g. a timeout)
        and returns None for this module specifically -- get_wind_forecast must check for that
        rather than pass None straight into pred_json_to_dict, which would blow up."""
        cache.clear()
        zone = tz.eastern
        now = datetime(2026, 1, 1, tzinfo=zone)
        timeline = GraphTimeline(date(2026, 1, 1), date(2026, 1, 1), zone, now=now)
        station = boot.load_station("welinwq")

        with (
            patch.object(wind, "pull_data", return_value=None),
            patch.object(wind, "pred_json_to_dict") as mock_pred_json_to_dict,
        ):
            result = wind.get_wind_forecast(station, timeline, hilo_mode=False)
            mock_pred_json_to_dict.assert_not_called()

        self.assertEqual(result, {})
        # A None result must not be cached as if it were a successful (if empty) forecast.
        self.assertIsNone(cache.get("openmeteo-15"))

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
