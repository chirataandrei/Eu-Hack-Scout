from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

URL = "https://hackathons.hackclub.com/api/events/upcoming"


def fetch(http: HttpClient) -> list[Hackathon]:
    status, data = http.get_json(URL)
    if status != 200 or not isinstance(data, list):
        return []
    out: list[Hackathon] = []
    for raw in data:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()
        url = str(raw.get("website") or "").strip()
        if not name or not url:
            continue
        loc = ", ".join(p for p in (str(raw.get("city") or ""), str(raw.get("country") or "")) if p)
        if raw.get("virtual"):
            fmt = Format.ONLINE
        elif raw.get("hybrid"):
            fmt = Format.HYBRID
        else:
            fmt = Format.IN_PERSON
        out.append(
            Hackathon(
                name=name,
                organizer="Hack Club",
                url=url,
                source="hackclub",
                location=loc,
                format=fmt,
                start_date=parse_date(raw.get("start")),
                end_date=parse_date(raw.get("end")),
            )
        )
    return out
