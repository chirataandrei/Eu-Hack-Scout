import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from euhackscout.net.apify import ApifyState
from euhackscout.sources.apify_scout import item_to_hackathon


class ApifyStateTests(unittest.TestCase):
    def test_rollover_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = ApifyState(month="1999-01", runs=5, spent_usd=4.2, last_run="")
            state.save(path)
            loaded = ApifyState.load(path)
            self.assertEqual(loaded.runs, 0)
            self.assertEqual(loaded.spent_usd, 0.0)
            ok, _ = loaded.can_run()
            self.assertTrue(ok)

    def test_cooldown(self) -> None:
        now = datetime.now(timezone.utc)
        state = ApifyState(month=now.strftime("%Y-%m"), last_run=(now - timedelta(hours=1)).isoformat())
        ok, reason = state.can_run(now)
        self.assertFalse(ok)
        self.assertIn("cooldown", reason)


class ApifyScoutTests(unittest.TestCase):
    def test_google_hit_maps_to_bucharest(self) -> None:
        item = item_to_hackathon(
            {
                "title": "HackITAll 2026 — LSAC București",
                "url": "https://lsacbucuresti.ro/hackitall-2026/",
                "query_id": "hackathon Bucuresti 2026",
                "description": "24h student hackathon",
            }
        )
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.source, "apify")
        self.assertIn("Bucharest", item.location)

    def test_conference_title_still_maps_but_is_filterable(self) -> None:
        from euhackscout.filters import is_hackathon

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
