import json
import unittest
from datetime import date
from pathlib import Path

from euhackscout.filters import is_hackathon
from euhackscout.models import Format
from euhackscout.sources.aicrowd import hackathons_from_html as aicrowd_from_html
from euhackscout.sources.apify_scout import item_to_hackathon
from euhackscout.sources.cassini import hackathons_from_listing
from euhackscout.sources.engines.rss import parse_rss
from euhackscout.sources.engines.wordpress import hackathons_from_wp_posts
from euhackscout.sources.ethglobal import hackathons_from_rsc
from euhackscout.sources.meetup import hackathons_from_next_data
from euhackscout.sources.mlh import hackathons_from_inertia
from euhackscout.sources.taikai import hackathons_from_payload

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class WordpressLsacTests(unittest.TestCase):
    def test_hackitall_from_wp_fixture(self) -> None:
        posts = json.loads((FIXTURES / "lsac_wp.json").read_text())
        items = hackathons_from_wp_posts(
            posts, organizer="LSAC București", source="lsac", assume_bucharest=True
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "HackITAll 2026")
        self.assertIn("Bucharest", items[0].location)
        self.assertTrue(is_hackathon(items[0].name))
        self.assertNotEqual(items[0].start_date, date(2024, 3, 1))


class RssStartupcafeTests(unittest.TestCase):
    def test_only_hackathon_articles_pass_keyword(self) -> None:
        body = (FIXTURES / "startupcafe.rss").read_text()
        items = parse_rss(body)
        kept = [i for i in items if is_hackathon(i["title"])]
        self.assertEqual(len(kept), 1)
        self.assertIn("Hackathoane", kept[0]["title"])


class TaikaiTests(unittest.TestCase):
    def test_graphql_payload(self) -> None:
        payload = json.loads((FIXTURES / "taikai.json").read_text())
        items = hackathons_from_payload(payload)
        self.assertEqual(len(items), 2)
        cassini = next(i for i in items if "CASSINI" in i.name)
        self.assertEqual(cassini.format, Format.HYBRID)
        self.assertEqual(cassini.location, "Europe")


class MlhTests(unittest.TestCase):
    def test_emea_and_digital_kept_amer_dropped(self) -> None:
        html = (FIXTURES / "mlh.html").read_text()
        items = hackathons_from_inertia(html)
        names = {i.name for i in items}
        self.assertIn("DurHack", names)
        self.assertIn("Global Hack Week: Data", names)
        self.assertNotIn("HackNY", names)


class EthglobalTests(unittest.TestCase):
    def test_rsc_hackathons_keep_city(self) -> None:
        body = (FIXTURES / "ethglobal.html").read_text()
        items = hackathons_from_rsc(body)
        by_slug = {i.url.rsplit("/", 1)[-1]: i for i in items}
        self.assertIn("tokyo2026", by_slug)
        self.assertIn("Tokyo", by_slug["tokyo2026"].location)
        self.assertEqual(by_slug["tokyo2026"].format, Format.IN_PERSON)
        self.assertEqual(by_slug["ethonline2026"].format, Format.ONLINE)
        self.assertNotIn("pragma-tokyo2026", by_slug)


class CassiniTests(unittest.TestCase):
    def test_listing_not_tools_node(self) -> None:
        html = (FIXTURES / "cassini.html").read_text()
        items = hackathons_from_listing(html)
        self.assertEqual(len(items), 1)
        self.assertIn("12th CASSINI Hackathon", items[0].name)
        self.assertIn("Peace", items[0].name)
        self.assertNotIn("will take", items[0].name.lower())
        self.assertEqual(items[0].start_date, date(2026, 11, 27))
        self.assertEqual(items[0].end_date, date(2026, 11, 29))


class MeetupTests(unittest.TestCase):
    def test_apollo_event(self) -> None:
        html = (FIXTURES / "meetup.html").read_text()
        items = hackathons_from_next_data(html)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "Bucharest Student Hackathon")
        self.assertIn("București", items[0].location)


class AicrowdTests(unittest.TestCase):
    def test_skips_old_years_keeps_current(self) -> None:
        html = (FIXTURES / "aicrowd.html").read_text()
        items = aicrowd_from_html(html, today=date(2026, 8, 31))
        names = [i.name for i in items]
        self.assertTrue(any("arc white box" in n.lower() or "arc-white-box" in n.lower() for n in names))
        self.assertFalse(any("2024" in n for n in names))
        self.assertFalse(any("discourse" in n.lower() for n in names))


class ApifyMappingTests(unittest.TestCase):
    def test_google_lsac_hit_is_bucharest(self) -> None:
        item = item_to_hackathon(
            {
                "title": "HackITAll 2026 — LSAC București",
                "url": "https://lsacbucuresti.ro/hackitall-2026/",
                "query_id": "site:lsacbucuresti.ro hackathon",
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertIn("Bucharest", item.location)

    def test_conference_hit_is_not_a_hackathon(self) -> None:
        item = item_to_hackathon(
            {
                "title": "How to Web Conference 2026",
                "url": "https://www.howtoweb.co/",
                "query_id": "hackathon Bucuresti",
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertFalse(is_hackathon(item.name))


if __name__ == "__main__":
    unittest.main()
