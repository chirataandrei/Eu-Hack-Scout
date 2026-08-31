import unittest
from datetime import date

from euhackscout.filters import is_hackathon
from euhackscout.sources.engines.jsonld import events_from_html
from euhackscout.sources.engines.rss import parse_rss
from euhackscout.sources.engines.wordpress import hackathons_from_wp_posts


class WordpressTests(unittest.TestCase):
    def test_lsac_post(self) -> None:
        posts = [
            {
                "title": {"rendered": "HackITAll 2026"},
                "link": "https://lsacbucuresti.ro/hackitall-2026/",
                "content": {"rendered": "<p>4-5 aprilie 2026</p>"},
                "date": "2026-03-01T10:00:00",
            }
        ]
        items = hackathons_from_wp_posts(posts, organizer="LSAC", source="lsac", assume_bucharest=True)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "HackITAll 2026")
        self.assertIn("Bucharest", items[0].location)
        self.assertTrue(is_hackathon(items[0].name))


class RssTests(unittest.TestCase):
    def test_filters_by_parse_only(self) -> None:
        body = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Hackathoane de drone la București</title>
            <link>https://startupcafe.ro/hackathon-drone</link>
            <description>Înscrieri deschise pentru hackathonul din octombrie.</description>
          </item>
          <item>
            <title>How to Web Conference 2026</title>
            <link>https://startupcafe.ro/how-to-web</link>
            <description>Conferință, nu hackathon.</description>
          </item>
        </channel></rss>
        """
        items = parse_rss(body)
        self.assertEqual(len(items), 2)
        kept = [i for i in items if is_hackathon(i["title"])]
        self.assertEqual(len(kept), 1)
        self.assertIn("Hackathoane", kept[0]["title"])


class JsonLdTests(unittest.TestCase):
    def test_eventbrite_itemlist(self) -> None:
        html = """
        <script type="application/ld+json">
        {"@type":"ItemList","itemListElement":[
          {"@type":"ListItem","item":{
            "@type":"Event",
            "name":"WomenHack Bucharest",
            "url":"https://www.eventbrite.com/e/1",
            "startDate":"2026-12-09",
            "endDate":"2026-12-09",
            "eventAttendanceMode":"https://schema.org/OfflineEventAttendanceMode",
            "location":{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":"Bucharest","addressCountry":"RO"}}
          }}
        ]}
        </script>
        """
        events = events_from_html(html, page_url="https://www.eventbrite.com/d/romania--bucharest/hackathon/")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["name"], "WomenHack Bucharest")
        self.assertEqual(events[0]["start_date"], date(2026, 12, 9))
        self.assertIn("Bucharest", events[0]["location"])


if __name__ == "__main__":
    unittest.main()
