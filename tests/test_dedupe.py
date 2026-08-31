import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from euhackscout.models import Format, Hackathon
from euhackscout.pipeline import dedupe, route_bucket, write_shards
from euhackscout.store import canonical_name, fingerprint, split_new


def _h(**kwargs) -> Hackathon:
    defaults = dict(
        name="HackITAll 2026",
        organizer="LSAC",
        url="https://hack.lsacbucuresti.ro/",
        source="lsac",
        location="Bucharest, Romania",
        format=Format.IN_PERSON,
        start_date=date(2026, 4, 4),
    )
    defaults.update(kwargs)
    return Hackathon(**defaults)


class CanonicalNameTests(unittest.TestCase):
    def test_strips_year_and_edition(self) -> None:
        self.assertEqual(canonical_name("HackITAll 2026"), canonical_name("HackITAll"))
        self.assertEqual(canonical_name("BESTEM v14"), canonical_name("BESTEM"))
        self.assertEqual(canonical_name("Electron Hackathon #4"), canonical_name("Electron Hackathon"))


class FingerprintTests(unittest.TestCase):
    def test_cross_source_collapse(self) -> None:
        a = fingerprint(_h(source="lsac", url="https://hack.lsacbucuresti.ro/"))
        b = fingerprint(_h(source="apify", url="https://lsacbucuresti.ro/hackitall-2026/"))
        self.assertEqual(a, b)

    def test_different_events_differ(self) -> None:
        a = fingerprint(_h(name="HackITAll", start_date=date(2026, 4, 4)))
        b = fingerprint(_h(name="Electron Hackathon", start_date=date(2026, 4, 18)))
        self.assertNotEqual(a, b)


class DedupeTests(unittest.TestCase):
    def test_earlier_source_wins(self) -> None:
        luma = _h(source="luma", url="https://lu.ma/hackitall")
        apify = _h(source="apify", url="https://example.com/hackitall")
        out = dedupe([luma, apify])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].source, "luma")

    def test_split_new_uses_fingerprint(self) -> None:
        item = _h()
        seen = {fingerprint(item)}
        new, current = split_new([item], seen)
        self.assertEqual(new, [])
        self.assertEqual(len(current), 1)


class ShardTests(unittest.TestCase):
    def test_route_bucket(self) -> None:
        self.assertEqual(route_bucket(_h()), "bucharest")
        self.assertEqual(route_bucket(_h(location="Berlin, Germany")), "europe")
        self.assertEqual(route_bucket(_h(format=Format.ONLINE, location="Anywhere")), "online")

    def test_write_shards(self) -> None:
        import euhackscout.config as config

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config.BUCHAREST_PATH = root / "bucharest.json"
            config.EUROPE_PATH = root / "europe.json"
            config.ONLINE_PATH = root / "online.json"
            # write_shards imports paths at call time from config module... actually it imported names
            # so we patch pipeline module paths instead.
            import euhackscout.pipeline as pipeline

            pipeline.BUCHAREST_PATH = root / "bucharest.json"
            pipeline.EUROPE_PATH = root / "europe.json"
            pipeline.ONLINE_PATH = root / "online.json"
            buckets = write_shards(
                [
                    _h(),
                    _h(name="Junction", location="Helsinki, Finland", url="https://hackjunction.com/", start_date=date(2026, 11, 1)),
                    _h(name="Shipaton", format=Format.ONLINE, location="Online", url="https://devpost.com/shipaton"),
                ]
            )
            self.assertEqual(len(buckets["bucharest"]), 1)
            self.assertEqual(len(buckets["europe"]), 1)
            self.assertEqual(len(buckets["online"]), 1)
            payload = json.loads((root / "bucharest.json").read_text())
            self.assertEqual(payload["hackathons"][0]["name"], "HackITAll 2026")


if __name__ == "__main__":
    unittest.main()
