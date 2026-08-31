from __future__ import annotations

import re
from html import unescape

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date_range

LIST_URL = "https://www.cassini.eu/hackathons/"
NAME_RE = re.compile(
    r"(\d+(?:st|nd|rd|th)\s+CASSINI Hackathon"
    r"(?:\s*[-–]\s*(?:(?!will\b)[A-Za-z0-9,&']+\s*){1,8})?)",
    re.I,
)
DATES_RE = re.compile(
    r"(\d{1,2}\s*[-–]\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+20\d{2})",
    re.I,
)


def _plain(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html or "", flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text))


def hackathons_from_listing(html: str) -> list[Hackathon]:
    text = _plain(html)
    names = [re.sub(r"\s+", " ", n).strip(" -") for n in NAME_RE.findall(text)]
    names = [n for n in names if len(n) <= 90]
    if not names:
        return []
    themed = [n for n in names if "-" in n or "–" in n]
    name = max(themed or names, key=len)
    dates = DATES_RE.search(text)
    start, end = parse_date_range(dates.group(1) if dates else name)
    return [
        Hackathon(
            name=name,
            organizer="CASSINI",
            url=LIST_URL,
            source="cassini",
            location="Europe",
            format=Format.HYBRID,
            start_date=start,
            end_date=end,
            tags=("eu", "space"),
        )
    ]


def fetch(http: HttpClient) -> list[Hackathon]:
    status, body = http.get(LIST_URL, headers={"Accept": "text/html"})
    if status != 200 or not body:
        return []
    return hackathons_from_listing(body)
