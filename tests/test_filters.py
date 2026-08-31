import unittest
from datetime import date, timedelta

from euhackscout.filters import (
    is_active,
    is_bucharest,
    is_europe,
    is_hackathon,
    is_online,
    keep_hackathon,
)
from euhackscout.models import Format, Hackathon


def _h(**kwargs) -> Hackathon:
    defaults = dict(
        name="HackITAll",
        organizer="LSAC",
        url="https://hack.lsacbucuresti.ro/event",
        source="lsac",
        location="Bucharest, Romania",
        format=Format.IN_PERSON,
        start_date=date.today() + timedelta(days=30),
    )
    defaults.update(kwargs)
    return Hackathon(**defaults)


class LocationTests(unittest.TestCase):
    def test_bucharest_spellings(self) -> None:
        self.assertTrue(is_bucharest("București"))
        self.assertTrue(is_bucharest("Bucharest, Romania"))
        self.assertTrue(is_bucharest("Pipera, Ilfov"))
        self.assertFalse(is_bucharest("Cluj-Napoca"))

    def test_europe_includes_bucharest_and_london(self) -> None:
        self.assertTrue(is_europe("București"))
        self.assertTrue(is_europe("London, UK"))
        self.assertTrue(is_europe("Berlin, DE"))
        self.assertFalse(is_europe("New York, NY"))

    def test_online_format(self) -> None:
        self.assertTrue(is_online(Format.ONLINE))
        self.assertFalse(is_online(Format.IN_PERSON))


class KeywordTests(unittest.TestCase):
    def test_hackathon_titles(self) -> None:
        self.assertTrue(is_hackathon("HackITAll 2026"))
        self.assertTrue(is_hackathon("BESTEM v14"))
        self.assertTrue(is_hackathon("NASA Space Apps datathon"))
        self.assertFalse(is_hackathon("DevFest Bucharest"))
        self.assertFalse(is_hackathon("MeasureCamp Bucharest"))
        self.assertFalse(is_hackathon("How to Web Conference"))
        self.assertTrue(is_hackathon("NASA Space Apps Challenge"))
        self.assertTrue(is_hackathon("GitGood Hack 2026"))
        self.assertTrue(is_hackathon("Innovation Labs 2026"))
        self.assertTrue(is_hackathon("EESTEC Olympics"))

    def test_stale_year_in_title(self) -> None:
        self.assertFalse(keep_hackathon(_h(name="Retrospectivă HackITall II 2024", start_date=None)))
        self.assertTrue(keep_hackathon(_h(name="HackITAll 2026")))


class ActiveTests(unittest.TestCase):
    def test_deadline_passed(self) -> None:
        today = date(2026, 8, 31)
        self.assertFalse(is_active(_h(registration_deadline=date(2026, 8, 1)), today))
        self.assertTrue(is_active(_h(registration_deadline=date(2026, 9, 1)), today))

    def test_fallback_to_end_then_start(self) -> None:
        today = date(2026, 8, 31)
        self.assertFalse(is_active(_h(registration_deadline=None, end_date=date(2026, 8, 1)), today))
        self.assertTrue(is_active(_h(registration_deadline=None, end_date=None, start_date=date(2026, 9, 1)), today))

    def test_missing_dates_kept(self) -> None:
        self.assertTrue(is_active(_h(start_date=None, end_date=None, registration_deadline=None)))


class KeepTests(unittest.TestCase):
    def test_keeps_bucharest_in_person(self) -> None:
        self.assertTrue(keep_hackathon(_h()))

    def test_keeps_online_anywhere(self) -> None:
        self.assertTrue(keep_hackathon(_h(format=Format.ONLINE, location="San Francisco, CA")))

    def test_rejects_us_in_person(self) -> None:
        self.assertFalse(keep_hackathon(_h(location="New York, NY", format=Format.IN_PERSON)))

    def test_rejects_india_in_person(self) -> None:
        self.assertFalse(keep_hackathon(_h(location="Bangalore, India", format=Format.IN_PERSON)))

    def test_rejects_in_person_without_location(self) -> None:
        self.assertFalse(keep_hackathon(_h(location="", format=Format.IN_PERSON)))

    def test_assume_bucharest_fills_empty_location(self) -> None:
        self.assertTrue(keep_hackathon(_h(location="", format=Format.IN_PERSON), assume_bucharest=True))

    def test_keyword_gate(self) -> None:
        self.assertFalse(keep_hackathon(_h(name="DevFest Bucharest"), require_keyword=True))
        self.assertTrue(keep_hackathon(_h(), require_keyword=True))


if __name__ == "__main__":
    unittest.main()
