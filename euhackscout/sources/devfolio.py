from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

URL = "https://api.devfolio.co/api/hackathons?filter=upcoming&page={page}&limit=20"


def fetch(http: HttpClient) -> list[Hackathon]:
    out: list[Hackathon] = []
    seen: set[str] = set()
    for page in range(1, 6):
        status, data = http.get_json(URL.format(page=page))
        if status != 200 or not isinstance(data, dict):
            break
        rows = data.get("result") or data.get("hackathons") or []
        if not rows:
            break
        new = 0
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            slug = str(raw.get("slug") or "").strip()
            url = str(raw.get("uri") or "").strip() or (f"https://devfolio.co/hackathons/{slug}" if slug else "")
            if not name or not url or url in seen:
                continue
            seen.add(url)
            new += 1
            loc = str(raw.get("location") or "")
            city = str(raw.get("city") or "")
            country = str(raw.get("country") or "")
            if not loc:
                loc = ", ".join(p for p in (city, country) if p)
            fmt = Format.ONLINE if raw.get("is_online") else Format.IN_PERSON
            themes = []
            for theme in raw.get("themes") or []:
                if isinstance(theme, dict) and theme.get("name"):
                    themes.append(str(theme["name"]))
                elif isinstance(theme, str):
                    themes.append(theme)
            out.append(
                Hackathon(
                    name=name,
                    organizer="Devfolio",
                    url=url,
                    source="devfolio",
                    location=loc,
                    format=fmt,
                    start_date=parse_date(raw.get("starts_at")),
                    end_date=parse_date(raw.get("ends_at")),
                    tags=tuple(themes),
                )
            )
        if new == 0:
            break
    return out
