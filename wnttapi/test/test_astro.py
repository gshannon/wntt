# ruff: noqa: I001
import test._bootstrap as boot

from datetime import datetime
from unittest import TestCase
import json
from typing import Any

import app.datasource.astrotide as astro
from app.hilo import Hilo
import app.station as stn
import app.tzutil as tz
from app import util
from app.timeline import Timeline


class TestAstro(TestCase):
    station: stn.Station

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.station = boot.load_station("welinwq")

    def test_parse_15m_predictions(self):
        """Able to parse 15m predictions from a json list of predictions from API call."""

        zone = tz.eastern
        # file has entire day of data, but we'll extract just 1 hour
        start_dt = datetime(2025, 5, 6, 1, tzinfo=zone)
        end_dt = datetime(2025, 5, 6, 1, 45, tzinfo=zone)
        tline = Timeline(start_dt, end_dt)

        raw: str = util.read_file(f"{boot.test_data_dir}/astro-15m.json")
        json_dict: dict[str, Any] = json.loads(raw)

        plist = astro.validate_15m(
            json_dict, tline, self.station.navd88_feet_to_mllw_feet
        )

        preds_dict = astro.pred15_json_to_dict(plist, tline)
        self.assertEqual(len(preds_dict), 4)
        self.assertEqual(
            preds_dict[tline.requested_times[0]],
            self.station.navd88_feet_to_mllw_feet(-3.624),
        )
        self.assertEqual(
            preds_dict[tline.requested_times[1]],
            self.station.navd88_feet_to_mllw_feet(-3.621),
        )
        self.assertEqual(
            preds_dict[tline.requested_times[2]],
            self.station.navd88_feet_to_mllw_feet(-3.564),
        )
        self.assertEqual(
            preds_dict[tline.requested_times[3]],
            self.station.navd88_feet_to_mllw_feet(-3.452),
        )

    def test_parse_hilo_predictions(self):
        """Able to parse hi-low predictions from a json list of predictions from API call."""

        zone = tz.eastern
        start_dt = datetime(2025, 12, 3, 0, tzinfo=zone)
        end_dt = datetime(2025, 12, 4, 23, 45, tzinfo=zone)
        tline = Timeline(start_dt, end_dt)

        raw: str = util.read_file(f"{boot.test_data_dir}/astro-1day-hilo.json")
        json_dict: dict[str, Any] = json.loads(raw)

        plist = astro.validate_hilo(
            json_dict, tline, self.station.navd88_feet_to_mllw_feet
        )
        preds_dict = astro.hilo_json_to_dict(plist, tline)
        self.assertEqual(len(preds_dict), 8)

        # { "t": "2025-12-04 16:09", "v": "-6.781", "type": "L" },
        entry = preds_dict[datetime(2025, 12, 4, 16, 15, tzinfo=zone)]
        self.assertEqual(entry.value, self.station.navd88_feet_to_mllw_feet(-6.781))
        self.assertEqual(entry.hilo, Hilo.LOW)
        self.assertEqual(entry.real_dt, datetime(2025, 12, 4, 16, 9, tzinfo=zone))

    def test_api_error(self):
        """Able to handle API error."""
        raw = util.read_file(f"{boot.test_data_dir}/astro-error.json")
        json_dict: dict[str, Any] = json.loads(raw)
        self.assertRaisesRegex(
            Exception,
            "No Predictions data was found. Please make sure the Datum input is valid",
            astro.json_error_check,
            json_dict,
        )
