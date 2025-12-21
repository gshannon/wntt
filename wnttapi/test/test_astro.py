import os.path
from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

import app.datasource.astrotide as astro
import app.station as stn
import app.tzutil as tz
import app.util as util
from app.timeline import GraphTimeline, Timeline
from django import setup

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

csv_location = "/Users/gshannon/dev/work/docker/wntt/datamount/stations"
test_data_path = os.path.dirname(os.path.abspath(__file__))
station = stn.get_station("welinwq", csv_location)


class TestAstro(TestCase):
    def test_date_range(self):
        """Pulls correct date range for high/low predictions."""

        # mock astrotide.pull_data to validate parameters
        def mocked_data_pull(*args):
            # even though we asked for 2025-12-21 only, the API must pull the day before also
            self.assertEqual(args[2], "20251220")
            self.assertEqual(args[3], "20251222")
            return {}

        with patch("app.datasource.astrotide.pull_data", side_effect=mocked_data_pull):
            timeline = GraphTimeline(
                date(2025, 12, 21), date(2025, 12, 21), station.time_zone
            )
            astro.get_hilo_astro_tides(station, timeline)

    def test_parse_15m_predictions(self):
        """Able to parse 15m predictions from a json list of predictions from API call."""
        zone = tz.eastern
        raw = util.read_file(f"{test_data_path}/data/astro-15m.json")
        contents = astro.extract_json(raw)
        # file has entire day of data, but we'll extract just 1 hour
        start_dt = datetime(2025, 5, 6, 1, tzinfo=zone)
        end_dt = datetime(2025, 5, 6, 1, 45, tzinfo=zone)
        tline = Timeline(start_dt, end_dt)
        preds_dict = astro.pred15_json_to_dict(contents, tline, station)
        self.assertEqual(len(preds_dict), 4)
        self.assertEqual(
            preds_dict[tline._requested_times[0]],
            station.navd88_feet_to_mllw_feet(-3.624),
        )
        self.assertEqual(
            preds_dict[tline._requested_times[1]],
            station.navd88_feet_to_mllw_feet(-3.621),
        )
        self.assertEqual(
            preds_dict[tline._requested_times[2]],
            station.navd88_feet_to_mllw_feet(-3.564),
        )
        self.assertEqual(
            preds_dict[tline._requested_times[3]],
            station.navd88_feet_to_mllw_feet(-3.452),
        )

    def test_api_error(self):
        """Able to handle API error."""
        raw = util.read_file(f"{test_data_path}/data/astro-error.json")
        self.assertRaisesRegex(
            ValueError,
            "No Predictions data was found. Please make sure the Datum input is valid",
            astro.extract_json,
            raw,
        )
