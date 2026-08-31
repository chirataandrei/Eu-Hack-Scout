from __future__ import annotations

import re

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date, parse_date_range

LIST_URL = "https://devpost.com/api/hackathons?status[]=open&status[]=upcoming&page={page}"
PRIZE_RE = re.compile(r"<[^>]+>")


def _format(item: dict) -> Format:
    loc = ((item.get("displayed_location") or {}) or {}).get("location") or ""
    loc = str(loc).lower()
    icon = str(((item.get("displayed_location") or {}) or {}).get("icon") or "")
    if "online" in loc or icon == "globe":
        if " and " in loc or "," in loc:
            return Format.HYBRID
        return Format.ONLINE
    return Format.IN_PERSON


def fetch(http: HttpClient) -> list[Hackathon]:
    out: list[Hackathon] = []
    seen: set[str] = set()
    page = 1
    while page <= 25:
        status, data = http.get_json(LIST_URL.format(page=page))
        if status != 200 or not isinstance(data, dict):
            break
        rows = data.get("hackathons") or []
        if not rows:
            break
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("title") or "").strip()
            url = str(raw.get("url") or "").strip()
            if not name or not url or url in seen:
                continue
            seen.add(url)
            loc = str(((raw.get("displayed_location") or {}) or {}).get("location") or "")
            start, end = parse_date_range(raw.get("submission_period_dates"))
            themes = []
            for theme in raw.get("themes") or []:
                if isinstance(theme, dict) and theme.get("name"):
                    themes.append(str(theme["name"]))
            out.append(
                Hackathon(
                    name=name,
                    organizer=str(raw.get("organization_name") or "Devpost"),
                    url=url,
                    source="devpost",
                    location=loc,
                    format=_format(raw),
                    start_date=start,
                    end_date=end,
                    registration_deadline=end or parse_date(raw.get("submission_period_dates")),
                    tags=tuple(themes),
                )
            )
        meta = (data.get("meta") or {}).get("meta") or data.get("meta") or {}
        total = int(meta.get("total_count") or 0)
        per_page = int(meta.get("per_page") or len(rows) or 9)
        if page * per_page >= total:
            break
        page += 1
    return out
