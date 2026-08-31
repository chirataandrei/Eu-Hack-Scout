from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

URL = "https://earn.superteam.fun/api/listings/?type=hackathon"


def fetch(http: HttpClient) -> list[Hackathon]:
    status, data = http.get_json(URL)
    if status != 200:
        return []
    rows = data if isinstance(data, list) else (data.get("listings") or data.get("data") or []) if isinstance(data, dict) else []
    out: list[Hackathon] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type") or "").lower()
        if kind and kind != "hackathon":
            continue
        name = str(raw.get("title") or "").strip()
        slug = str(raw.get("slug") or "").strip()
        if not name:
            continue
        url = f"https://earn.superteam.fun/listing/{slug}" if slug else str(raw.get("url") or "")
        if not url:
            continue
        out.append(
            Hackathon(
                name=name,
                organizer="Superteam",
                url=url,
                source="superteam",
                location="Online",
                format=Format.ONLINE,
                registration_deadline=parse_date(raw.get("deadline")),
                tags=("web3",),
            )
        )
    return out
