from __future__ import annotations

import re
from datetime import date

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date_range

URL = "https://www.aicrowd.com/challenges"
HREF_RE = re.compile(r'href="(/challenges/([a-z0-9][-a-z0-9]{6,}))"', re.I)
SKIP_SLUGS = {"challenges", "new", "forum"}


def hackathons_from_html(html: str, *, today: date | None = None) -> list[Hackathon]:
    today = today or date.today()
    out: list[Hackathon] = []
    seen: set[str] = set()
    for path, slug in HREF_RE.findall(html or ""):
        slug = slug.strip("/")
        if slug.lower() in SKIP_SLUGS or "/" in path[len("/challenges/") :]:
            continue
        url = f"https://www.aicrowd.com{path}"
        if url in seen:
            continue
        seen.add(url)
        name = slug.replace("-", " ").strip()
        name = re.sub(r"\s+", " ", name)
        if name:
            name = name[0].upper() + name[1:]
        years = [int(y) for y in re.findall(r"\b(20\d{2})\b", name)]
        if years and max(years) < today.year:
            continue
        start, end = parse_date_range(name)
        out.append(
            Hackathon(
                name=name,
                organizer="AIcrowd",
                url=url,
                source="aicrowd",
                location="Online",
                format=Format.ONLINE,
                start_date=start,
                end_date=end,
                tags=("ai", "datathon"),
            )
        )
        if len(out) >= 40:
            break
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    status, body = http.get(URL, headers={"Accept": "text/html"})
    if status != 200 or not body:
        return []
    return hackathons_from_html(body)
