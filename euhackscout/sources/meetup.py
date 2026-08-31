from __future__ import annotations

import json
import re
from typing import Any

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

NEXT_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
SEARCH_URLS = (
    "https://www.meetup.com/find/?keywords=hackathon&location=ro--Bucharest&source=EVENTS",
    "https://www.meetup.com/find/?keywords=hackathon&location=gb--London&source=EVENTS",
    "https://www.meetup.com/find/?keywords=hackathon&location=de--Berlin&source=EVENTS",
    "https://www.meetup.com/find/?keywords=hackathon&location=fr--Paris&source=EVENTS",
)


def _resolve(state: dict[str, Any], node: Any) -> Any:
    if isinstance(node, dict) and isinstance(node.get("__ref"), str):
        return state.get(node["__ref"]) or node
    return node


def hackathons_from_next_data(body: str) -> list[Hackathon]:
    match = NEXT_RE.search(body or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    state = ((data.get("props") or {}).get("pageProps") or {}).get("__APOLLO_STATE__") or {}
    if not isinstance(state, dict):
        return []
    out: list[Hackathon] = []
    seen: set[str] = set()
    for key, event in state.items():
        if not str(key).startswith("Event:") or not isinstance(event, dict):
            continue
        name = str(event.get("title") or event.get("name") or "").strip()
        url = str(event.get("eventUrl") or event.get("url") or "").strip()
        if url and not url.startswith("http"):
            url = f"https://www.meetup.com{url}"
        if not name or not url or url in seen:
            continue
        seen.add(url)
        venue = _resolve(state, event.get("venue"))
        loc = ""
        if isinstance(venue, dict):
            loc = ", ".join(
                str(venue.get(k) or "") for k in ("city", "localizedLocation", "name", "country") if venue.get(k)
            )
        group = _resolve(state, event.get("group"))
        organizer = "Meetup"
        if isinstance(group, dict):
            organizer = str(group.get("name") or organizer)
        is_online = str(event.get("eventType") or "").upper() in {"ONLINE", "VIRTUAL"} or bool(
            event.get("isOnline") or event.get("onlineVenue")
        )
        out.append(
            Hackathon(
                name=name,
                organizer=organizer,
                url=url,
                source="meetup",
                location=loc,
                format=Format.ONLINE if is_online else Format.IN_PERSON,
                start_date=parse_date(event.get("dateTime") or event.get("startTime") or event.get("time")),
            )
        )
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    out: list[Hackathon] = []
    seen: set[str] = set()
    for url in SEARCH_URLS:
        status, body = http.get(url, headers={"Accept": "text/html"})
        if status != 200 or not body:
            continue
        for item in hackathons_from_next_data(body):
            if item.url in seen:
                continue
            seen.add(item.url)
            out.append(item)
    return out
