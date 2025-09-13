import json
import os.path
from datetime import datetime
from unittest import TestCase

import app.datasource.moon as moon
import app.tzutil as tz
import app.util as util
from app.timeline import GraphTimeline

path = os.path.dirname(os.path.abspath(__file__))


class TestMoon(TestCase):
    def test_current_moon_phases(self):
        """Able to get current phases of moon from JSON data"""
        zone = tz.eastern

        raw = util.read_file(f"{path}/data/moon1.json")
        contents = json.loads(raw)

        # This is the last minute before the New Moon starts.
        asof = datetime(2025, 9, 21, 15, 53, tzinfo=zone)
        data = moon.parse_json_current(contents, zone, asof)
        expected = {
            "current": "Last Quarter",
            "currentdt": datetime(2025, 9, 14, 6, 33, tzinfo=zone),
            "nextphase": "New Moon",
            "nextdt": datetime(2025, 9, 21, 15, 54, tzinfo=zone),
        }
        self.assertEqual(data, expected)

        # This is the exact minute the New Moon starts. It's now the current phase.
        asof = datetime(2025, 9, 21, 15, 54, tzinfo=zone)
        data = moon.parse_json_current(contents, zone, asof)
        expected = {
            "current": "New Moon",
            "currentdt": datetime(2025, 9, 21, 15, 54, tzinfo=zone),
            "nextphase": "First Quarter",
            "nextdt": datetime(2025, 9, 29, 19, 54, tzinfo=zone),
        }
        self.assertEqual(data, expected)

    def test__moon_phases_failure(self):
        """Able to get phases of moon from JSON data"""
        zone = tz.eastern

        raw = util.read_file(f"{path}/data/moon1.json")
        contents = json.loads(raw)

        asof = datetime(2025, 8, 15, 0, tzinfo=zone)
        data = moon.parse_json_current(contents, zone, asof)
        expected = {
            "current": None,
            "currentdt": None,
            "nextdt": None,
            "nextphase": None,
        }

        self.assertEqual(data, expected)

    def test_timeline_moon_phases(self):
        """Able to get current phases of moon from JSON data"""
        zone = tz.eastern
        start_date = datetime(2025, 9, 11, tzinfo=zone)
        end_date = datetime(2025, 9, 15, tzinfo=zone)
        timeline = GraphTimeline(start_date, end_date, zone)
        times = timeline.get_final_times({})

        raw = util.read_file(f"{path}/data/moon1.json")
        contents = json.loads(raw)

        data = moon.parse_json_timeline_old(contents, times)
        expected = {
            "phase": "Last Quarter",
            "phasedt": datetime(2025, 9, 14, 6, 33, tzinfo=zone),
        }
        self.assertEqual(data, expected)
