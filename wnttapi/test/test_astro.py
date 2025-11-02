import os.path
from datetime import datetime
from unittest import TestCase

import app.datasource.astrotide as astro
import app.tzutil as tz
import app.util as util
from app.timeline import Timeline

path = os.path.dirname(os.path.abspath(__file__))

station = "8419317"


class TestAstro(TestCase):
    def test_find_highest(self):
        """Able to get the highest tide from a json list of hi/lo values from API call."""

        raw = util.read_file(f"{path}/data/astro_hilo_2027.json")
        contents = astro.extract_json(raw)
        highest = astro.find_highest_navd88(contents)
        expected_high_navd88 = round(6.019, 2)
        self.assertEqual(highest, expected_high_navd88)

    def test_parse_15m_predictions(self):
        """Able to parse 15m predictions from a json list of predictions from API call."""
        zone = tz.eastern
        raw = util.read_file(f"{path}/data/astro_15m.json")
        contents = astro.extract_json(raw)
        # file has entire day of data, but we'll extract just 1 hour
        start_dt = datetime(2025, 5, 6, 1, tzinfo=zone)
        end_dt = datetime(2025, 5, 6, 1, 45, tzinfo=zone)
        tline = Timeline(start_dt, end_dt)
        preds_dict = astro.pred15_json_to_dict(contents, tline, station)
        self.assertEqual(len(preds_dict), 4)
        self.assertEqual(
            preds_dict[tline._requested_times[0]],
            util.navd88_feet_to_mllw_feet(-3.624, station),
        )
        self.assertEqual(
            preds_dict[tline._requested_times[1]],
            util.navd88_feet_to_mllw_feet(-3.621, station),
        )
        self.assertEqual(
            preds_dict[tline._requested_times[2]],
            util.navd88_feet_to_mllw_feet(-3.564, station),
        )
        self.assertEqual(
            preds_dict[tline._requested_times[3]],
            util.navd88_feet_to_mllw_feet(-3.452, station),
        )

    def test_parse_hilo_predictions(self):
        """Able to parse certain hi/lo predictions from a json list of predictions from API call."""
        raw = util.read_file(f"{path}/data/astro_hilo_3days.json")
        contents = astro.extract_json(raw)
        # file has 3 days of hilos, 5/6/25 - 5/8/25. If we ask for the entire timeline, but
        # set the cutoff for 5/7 19:00, we should just get the 4 values from 5/8.
        zone = tz.eastern
        start_dt = datetime(2025, 5, 6, tzinfo=zone)
        end_dt = datetime(2025, 5, 8, 23, 45, tzinfo=zone)
        hilo_start_dt = datetime(2025, 5, 7, 19, tzinfo=zone)
        timeline = Timeline(start_dt, end_dt)
        preds = astro.hilo_json_to_dict(contents, timeline, hilo_start_dt, station)
        self.assertEqual(len(preds), 4)
        self.assertEqual(
            preds[datetime(2025, 5, 8, 1, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 0, 58, tzinfo=zone),
                "value": util.navd88_feet_to_mllw_feet(3.554, station),
                "type": "H",
            },
        )
        self.assertEqual(
            preds[datetime(2025, 5, 8, 7, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 7, 6, tzinfo=zone),
                "value": util.navd88_feet_to_mllw_feet(-4.084, station),
                "type": "L",
            },
        )
        self.assertEqual(
            preds[datetime(2025, 5, 8, 13, 15, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 13, 21, tzinfo=zone),
                "value": util.navd88_feet_to_mllw_feet(3.294, station),
                "type": "H",
            },
        )
        self.assertEqual(
            preds[datetime(2025, 5, 8, 19, 30, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 19, 23, tzinfo=zone),
                "value": util.navd88_feet_to_mllw_feet(-4.093, station),
                "type": "L",
            },
        )

    def test_api_error(self):
        """Able to handle API error."""
        raw = util.read_file(f"{path}/data/astro_error.json")
        self.assertRaisesRegex(
            ValueError,
            "No Predictions data was found. Please make sure the Datum input is valid",
            astro.extract_json,
            raw,
        )
