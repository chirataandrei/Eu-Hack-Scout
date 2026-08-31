import unittest
from datetime import date

from euhackscout.models import Format, Hackathon, parse_date, parse_date_range


def _h(**kwargs) -> Hackathon:
    defaults = dict(
        name="HackITAll",
        organizer="LSAC",
        url="https://hack.lsacbucuresti.ro/",
        source="lsac",
        location="Bucharest, Romania",
        format=Format.IN_PERSON,
    )
    defaults.update(kwargs)
    return Hackathon(**defaults)


class ParseDateTests(unittest.TestCase):
    def test_iso(self) -> None:
        self.assertEqual(parse_date("2026-10-01T12:00:00Z"), date(2026, 10, 1))

    def test_human_range_uses_end(self) -> None:
        start, end = parse_date_range("Jul 31 - Oct 01, 2026")
        self.assertEqual(start, date(2026, 7, 31))
        self.assertEqual(end, date(2026, 10, 1))

    def test_romanian_range(self) -> None:
        start, end = parse_date_range("21-22 martie 2026")
        self.assertEqual(start, date(2026, 3, 21))
        self.assertEqual(end, date(2026, 3, 22))

    def test_bestem_style(self) -> None:
        start, end = parse_date_range("6 - 7 December 2025")
        self.assertEqual(start, date(2025, 12, 6))
        self.assertEqual(end, date(2025, 12, 7))

    def test_day_month_uses_nearby_year_not_css_pixels(self) -> None:
        start, end = parse_date_range(
            "NEXXT AI Hackathon 2025 până pe 28 octombrie. min-width:2028px"
        )
        self.assertEqual(start, date(2025, 10, 28))
        self.assertEqual(end, date(2025, 10, 28))


class UidTests(unittest.TestCase):
    def test_stable_across_url_noise(self) -> None:
        a = _h(url="https://www.example.com/event/?ref=x")
        b = _h(url="http://example.com/event")
        self.assertEqual(a.uid, b.uid)
        self.assertTrue(a.uid.startswith("hk:"))

    def test_name_folding(self) -> None:
        a = _h(name="HackITAll")
        b = _h(name="hackitall")
        self.assertEqual(a.uid, b.uid)

    def test_to_dict_serializes_dates(self) -> None:
        payload = _h(start_date=date(2026, 4, 4), format=Format.HYBRID).to_dict()
        self.assertEqual(payload["start_date"], "2026-04-04")
        self.assertEqual(payload["format"], "hybrid")
        self.assertIn("uid", payload)


if __name__ == "__main__":
    unittest.main()
