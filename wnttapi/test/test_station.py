# ruff: noqa: I001
import test._bootstrap  # noqa: F401  (configures Django; must precede app.* imports)

import os.path
from unittest import TestCase

import app.station as stn
from app.util import InternalError

test_data_path = os.path.dirname(os.path.abspath(__file__)) + "/data"
clean_test_file = "stations-clean.json"
wells_id = "welinwq"


class TestStation(TestCase):
    def test_all_stations(self):
        stations = stn.get_all_stations(
            test_data_path, clean_test_file, force_reload=True
        )
        self.assertTrue(wells_id in stations)
        self.assertEqual(len(stations), 2)

    def test_get_station(self):
        wells = stn.get_station(
            wells_id, test_data_path, clean_test_file, force_reload=True
        )
        self.assertIsNotNone(wells)

        # read from cache
        wells = stn.get_station(
            wells_id, test_data_path, clean_test_file, force_reload=False
        )
        self.assertIsNotNone(wells)

    def test_get_stations_api(self):
        json_content = stn.get_all_stations_api(
            test_data_path, clean_test_file, force_reload=True
        )
        self.assertEqual(json_content[wells_id]["id"], wells_id)

    def test_bad_json(self):
        with self.assertRaises(InternalError):
            # This file has a lat value as string instead of float
            stn.get_all_stations(test_data_path, "stations-bad.json", force_reload=True)
