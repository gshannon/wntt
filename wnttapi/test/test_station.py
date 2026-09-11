# ruff: noqa: I001
import test._bootstrap as boot

from unittest import TestCase
from django.core.cache import cache
from zoneinfo import ZoneInfo

import app.station as stn
from app.util import InternalError

clean_test_file = "stations-clean.json"
wells_id = "welinwq"


class TestStation(TestCase):
    def test_production_file(self):
        cache.clear()
        stations = stn.get_all_stations(data_dir=f"{boot.prod_data_root_dir}/stations")
        self.assertTrue(wells_id in stations)
        self.assertGreaterEqual(len(stations), 1)

    def test_get_station(self):
        cache.clear()
        wells1 = boot.load_station("welinwq")
        self.assertEqual(wells1.id, "welinwq")
        self.assertEqual(wells1.time_zone, ZoneInfo("US/Eastern"))

        # read from cache
        self.assertTrue(cache.has_key(stn.stations_cls_cache_key))
        wells2 = boot.load_station("welinwq")
        self.assertEqual(wells1, wells2)

    def test_get_stations_api(self):
        cache.clear()
        json_content = stn.get_all_stations_api(
            data_dir=f"{boot.prod_data_root_dir}/stations"
        )
        self.assertEqual(json_content[wells_id]["id"], wells_id)

    def test_bad_json(self):
        with self.assertRaises(InternalError):
            # This file has a lat value as string instead of float
            stn.get_all_stations(
                boot.test_data_dir, "stations-bad.json", force_reload=True
            )
