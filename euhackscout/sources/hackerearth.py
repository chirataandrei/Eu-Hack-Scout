from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

URL = "https://www.hackerearth.com/chrome-extension/events/"


def fetch(http: HttpClient) -> list[Hackathon]:
    status, data = http.get_json(URL)
    if status != 200 or not isinstance(data, dict):
        return []
    out: list[Hackathon] = []
    for raw in data.get("response") or []:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        if not name or not url:
            continue
        if url and not url.startswith("http"):
            url = f"https://www.hackerearth.com{url}"
        college = raw.get("college")
        if isinstance(college, str) and college.strip() and college.lower() not in {"false", "true"}:
            loc = college.strip()
            fmt = Format.IN_PERSON
        else:
            loc = "Online"
            fmt = Format.ONLINE
        challenge = str(raw.get("challenge_type") or "").lower()
        if "online" in challenge:
            fmt = Format.ONLINE
            loc = loc or "Online"
        out.append(
            Hackathon(
                name=name,
                organizer="HackerEarth",
                url=url,
                source="hackerearth",
                location=loc,
                format=fmt,
                start_date=parse_date(raw.get("start_utc_tz") or raw.get("start_timestamp") or raw.get("date")),
                end_date=parse_date(raw.get("end_utc_tz") or raw.get("end_timestamp") or raw.get("end_date")),
            )
        )
    return out
