import json
import os.path
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

import app.datasource.astrotide as astro
import app.datasource.cdmo as cdmo
import app.station as stn
import app.tzutil as tz
import app.util as util
from app.timeline import GraphTimeline, Timeline
from django import setup
from rest_framework.exceptions import APIException

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()

csv_location = "/Users/gshannon/dev/work/docker/wntt/datamount/stations"
test_data_path = os.path.dirname(os.path.abspath(__file__))
station = stn.get_station("welinwq", csv_location)


class TestAstro(TestCase):
    def mocked_data_pull(*args):
        interval = args[2]
        if interval == "hilo":
            raw = util.read_file(f"{test_data_path}/data/astro-1day-hilo.json")
            return astro.extract_json(raw)
        raise APIException("Invalid args to mocked_data_pull")

    def test_early_observed_hilo(self):
        """The situation is:
        - We're in HILO mode, where one or more observed hi/lo's are in the past, and one or more are predicted in the future.
        - The prediction that corresponds to the last observed hi/lo is rounded to a later 15-min block than the observed hi/lo time.
        In this case, we were showing both the observed and predicted hi/lo tides, close together in the timeline,
        because we were pulling predictions after the last observed *hi/lo* time, not the last observed *15-min* time. Here we
        test that we only succeed when we use the last observed 15-min time to determine where to start pulling predictions.
        """
        with patch(
            "app.datasource.astrotide.pull_data", side_effect=self.mocked_data_pull
        ):
            zone = tz.eastern
            start_dt = datetime(2025, 12, 3, tzinfo=zone)
            end_dt = datetime(2025, 12, 3, tzinfo=zone)
            # Pretend it's 9:40 -- not late enough to have the observed 9:00 high tide yet, due to reporting lag.
            current_dt = datetime(2025, 12, 3, 9, 40, tzinfo=zone)
            timeline = GraphTimeline(start_dt, end_dt, zone, current_dt)
            # Simulate getting observed tides from CDMO up to current time.
            # Load json from file with observed tides up to 8:30, converting the keys to datetime
            raw_obs = util.read_file(f"{test_data_path}/data/cdmo-partial-day.json")
            json_dict = json.loads(raw_obs)
            obs_dict = {
                datetime.fromisoformat(k).replace(tzinfo=zone): v
                for k, v in json_dict.items()
            }
            # Find observed hi/lo tides from observed 15-min data.  Latest one is the Low at 02:15.
            obs_hilo_dict = cdmo.find_hilos(timeline, obs_dict)
            self.assertEqual(
                max(obs_hilo_dict), datetime(2025, 12, 3, 2, 15, tzinfo=zone)
            )
            # First we'll do it the wrong way and pull predicted hilos since the latest observed hilo.
            # Our earliest predicted tide will be only 15 min after last observed hilo.
            pred_hilo = astro.get_hilo_astro_tides(
                station, timeline, max(obs_hilo_dict)
            )
            self.assertEqual(min(pred_hilo), max(obs_hilo_dict) + timedelta(minutes=15))
            # Now do it the right way, using last observed 15-min time. Earliest predicted is > 5 hours later.
            pred_hilo = astro.get_hilo_astro_tides(station, timeline, max(obs_dict))
            self.assertGreaterEqual(
                min(pred_hilo), max(obs_hilo_dict) + timedelta(hours=5)
            )

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

    def test_parse_hilo_predictions(self):
        """Able to parse certain hi/lo predictions from a json list of predictions from API call."""
        raw = util.read_file(f"{test_data_path}/data/astro-hilo-3days.json")
        contents = astro.extract_json(raw)
        # file has 3 days of hilos, 5/6/25 - 5/8/25. If we ask for the entire timeline, but
        # set the cutoff for 5/7 19:00, we should just get the 4 values from 5/8.
        zone = tz.eastern
        start_dt = datetime(2025, 5, 6, tzinfo=zone)
        end_dt = datetime(2025, 5, 8, 23, 45, tzinfo=zone)
        hilo_start_dt = datetime(2025, 5, 7, 19, tzinfo=zone)
        timeline = Timeline(start_dt, end_dt)
        preds = astro.hilo_json_to_dict(station, contents, timeline, hilo_start_dt)
        self.assertEqual(len(preds), 4)
        self.assertEqual(
            preds[datetime(2025, 5, 8, 1, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 0, 58, tzinfo=zone),
                "value": station.navd88_feet_to_mllw_feet(3.554),
                "type": "H",
            },
        )
        self.assertEqual(
            preds[datetime(2025, 5, 8, 7, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 7, 6, tzinfo=zone),
                "value": station.navd88_feet_to_mllw_feet(-4.084),
                "type": "L",
            },
        )
        self.assertEqual(
            preds[datetime(2025, 5, 8, 13, 15, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 13, 21, tzinfo=zone),
                "value": station.navd88_feet_to_mllw_feet(3.294),
                "type": "H",
            },
        )
        self.assertEqual(
            preds[datetime(2025, 5, 8, 19, 30, tzinfo=zone)],
            {
                "real_dt": datetime(2025, 5, 8, 19, 23, tzinfo=zone),
                "value": station.navd88_feet_to_mllw_feet(-4.093),
                "type": "L",
            },
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
