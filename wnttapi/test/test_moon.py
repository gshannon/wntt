import os

from datetime import datetime
from unittest import TestCase

import app.datasource.moon as moon
import app.tzutil as tz
from app.timeline import GraphTimeline
from django import setup

csv_location = "/Users/gshannon/dev/work/docker/wntt/datamount/syzygy"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.dev")
setup()


class TestMoon(TestCase):
    def test_current_moon_phases(self):
        """Able to get current phases of moon from JSON data"""
        zone = tz.eastern

        # This is the last minute before the New Moon starts.
        asof = datetime(2025, 9, 21, 15, 53, tzinfo=zone)
        data = moon.get_current_moon_phases(zone, asof, csv_location)
        expected = {
            "current": "LQ",
            "currentdt": datetime(2025, 9, 14, 6, 33, tzinfo=zone),
            "nextphase": "NM",
            "nextdt": datetime(2025, 9, 21, 15, 54, tzinfo=zone),
        }
        self.assertEqual(data, expected)

        # This is the exact minute the New Moon starts. It's now the current phase.
        asof = datetime(2025, 9, 21, 15, 54, tzinfo=zone)
        data = moon.get_current_moon_phases(zone, asof)
        expected = {
            "current": "NM",
            "currentdt": datetime(2025, 9, 21, 15, 54, tzinfo=zone),
            "nextphase": "FQ",
            "nextdt": datetime(2025, 9, 29, 19, 54, tzinfo=zone),
        }
        self.assertEqual(data, expected)

    def test_timeline_moon_phases(self):
        """Able to get current phases of moon from JSON data"""
        zone = tz.eastern
        start_date = datetime(2025, 9, 11, tzinfo=zone)
        end_date = datetime(2025, 9, 15, tzinfo=zone)
        timeline = GraphTimeline(start_date, end_date, zone)

        data = moon.get_moon_phase(timeline)
        expected = ("LQ", datetime(2025, 9, 14, 6, 33, tzinfo=zone))
        self.assertEqual(data, expected)

    def test_perigee_over_year(self):
        """Able to get perigee over year boundary"""
        zone = tz.eastern
        start_date = datetime(2025, 12, 31, tzinfo=zone)
        end_date = datetime(2026, 1, 4, tzinfo=zone)
        timeline = GraphTimeline(start_date, end_date, zone)
        expected = datetime(2026, 1, 1, 16, 45, tzinfo=zone)
        self.assertEqual(expected, moon.get_perigee(timeline, csv_location))

    def test_perihelion_over_year(self):
        """Able to get perihelion over year boundary"""
        zone = tz.eastern
        start_date = datetime(2025, 12, 31, tzinfo=zone)
        end_date = datetime(2026, 1, 4, tzinfo=zone)
        timeline = GraphTimeline(start_date, end_date, zone)
        expected = datetime(2026, 1, 3, 12, 16, tzinfo=zone)
        self.assertEqual(expected, moon.get_perihelion(timeline, csv_location))
