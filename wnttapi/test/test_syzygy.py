# ruff: noqa: I001
import test._bootstrap as boot

from datetime import date, datetime
from unittest import TestCase
from django.core.cache import cache

from app.datasource import syzygy
import app.tzutil as tz
from app.timeline import GraphTimeline

csv_location = f"{boot.test_data_dir}/../../../datamount/syzygy"
bad_location = "/no-such-directory"


class TestSyzygy(TestCase):
    def test_current_moon_phases(self):
        """Able to get current phases of moon from JSON data"""
        zone = tz.eastern

        # This is the last minute before the New Moon starts.
        asof = datetime(2025, 9, 21, 15, 53, tzinfo=zone)
        data = syzygy.get_current_moon_phases(zone, asof, csv_location)
        expected = {
            "current": syzygy.LAST_QUARTER,
            "currentdt": datetime(2025, 9, 14, 6, 33, tzinfo=zone),
            "nextphase": syzygy.NEW_MOON,
            "nextdt": datetime(2025, 9, 21, 15, 54, tzinfo=zone),
        }
        self.assertEqual(data, expected)

        # This is the exact minute the New Moon starts. It's now the current phase.
        asof = datetime(2025, 9, 21, 15, 54, tzinfo=zone)
        data = syzygy.get_current_moon_phases(zone, asof)
        expected = {
            "current": syzygy.NEW_MOON,
            "currentdt": datetime(2025, 9, 21, 15, 54, tzinfo=zone),
            "nextphase": syzygy.FIRST_QUARTER,
            "nextdt": datetime(2025, 9, 29, 19, 54, tzinfo=zone),
        }
        self.assertEqual(data, expected)

    def test_current_moon_phases_error_does_not_raise(self):
        """Able to get current phases of moon from cvs data"""
        cache.clear()
        data = syzygy.get_current_moon_phases(tzone=tz.eastern, data_dir=bad_location)
        self.assertEqual(
            data,
            {"current": None, "currentdt": None, "nextphase": None, "nextdt": None},
        )

    def test_full_syzygy(self):
        """Able to get all syzygy data for a timeline"""
        zone = tz.eastern
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 4)
        timeline = GraphTimeline(start_date, end_date, zone)

        data = syzygy.get_syzygy_data(timeline, data_dir=csv_location)
        expected = [
            {
                "code": syzygy.FULL_MOON,
                "real_dt": datetime(2026, 1, 3, 5, 3, tzinfo=zone),
            },
            {
                "code": syzygy.PERIGEE,
                "real_dt": datetime(2026, 1, 1, 16, 45, tzinfo=zone),
            },
            {
                "code": syzygy.PERIHELION,
                "real_dt": datetime(2026, 1, 3, 12, 16, tzinfo=zone),
            },
        ]
        self.assertEqual(data, expected)

    def test_full_syzygy_failure_does_not_raise(self):
        """Failure while getting all syzygy data for a timeline does not raise exception"""
        cache.clear()
        timeline = GraphTimeline(date(2026, 1, 1), date(2026, 1, 4), tz.eastern)
        data = syzygy.get_syzygy_data(timeline, data_dir=bad_location)
        self.assertEqual(data, [])

    def test_perigee_over_year(self):
        """Able to get perigee over year boundary"""
        zone = tz.eastern
        start_date = date(2025, 12, 31)
        end_date = date(2026, 1, 4)
        timeline = GraphTimeline(start_date, end_date, zone)
        expected = datetime(2026, 1, 1, 16, 45, tzinfo=zone)
        self.assertEqual(expected, syzygy.get_perigee(timeline, csv_location))

    def test_perigee_failure_does_not_raise(self):
        cache.clear()
        zone = tz.eastern
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 4)
        timeline = GraphTimeline(start_date, end_date, zone)
        perigee_times = syzygy.get_perigee(timeline=timeline, data_dir=bad_location)
        self.assertIsNone(perigee_times)

    def test_perihelion_over_year(self):
        """Able to get perihelion over year boundary"""
        zone = tz.eastern
        start_date = date(2025, 12, 31)
        end_date = date(2026, 1, 4)
        timeline = GraphTimeline(start_date, end_date, zone)
        expected = datetime(2026, 1, 3, 12, 16, tzinfo=zone)
        self.assertEqual(expected, syzygy.get_perihelion(timeline, csv_location))
