from __future__ import annotations

import re

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

URL = "https://ethglobal.com/events"
EVENT_RE = re.compile(
    r'\\"name\\":\\"([^\\"]+)\\",\\"slug\\":\\"([^\\"]+)\\",\\"type\\":\\"hackathon\\",'
    r'\\"medium\\":\\"([^\\"]+)\\",\\"startTime\\":\\"([^\\"]+)\\",\\"endTime\\":\\"([^\\"]+)\\"'
)
CITY_RE = re.compile(
    r'\\"city\\":\{[^}]*\\"name\\":\\"([^\\"]+)\\".*?\\"country\\":\{[^}]*\\"name\\":\\"([^\\"]+)\\"',
    re.S,
)


def hackathons_from_rsc(body: str) -> list[Hackathon]:
    out: list[Hackathon] = []
    seen: set[str] = set()
    for match in EVENT_RE.finditer(body or ""):
        name, slug, medium, start, end = match.groups()
        url = f"https://ethglobal.com/events/{slug}"
        if url in seen:
            continue
        seen.add(url)
        virtual = medium.lower() in {"virtual", "online", "digital"}
        loc = "Online" if virtual else ""
        prefix = body[max(0, match.start() - 400) : match.start()]
        city_match = CITY_RE.search(prefix)
        if city_match and not virtual:
            loc = f"{city_match.group(1)}, {city_match.group(2)}"
        out.append(
            Hackathon(
                name=name.replace("\\u0026", "&"),
                organizer="ETHGlobal",
                url=url,
                source="ethglobal",
                location=loc,
                format=Format.ONLINE if virtual else Format.IN_PERSON,
                start_date=parse_date(start),
                end_date=parse_date(end),
                tags=("web3",),
            )
        )
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    status, body = http.get(URL, headers={"Accept": "text/html"})
    if status != 200 or not body:
        return []
    return hackathons_from_rsc(body)
