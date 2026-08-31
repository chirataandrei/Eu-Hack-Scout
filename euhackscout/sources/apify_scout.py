"""Read-only Apify cache → Hackathon list. The daily scan never talks to Apify."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from euhackscout.config import APIFY_CACHE_PATH
from euhackscout.filters import is_bucharest
from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date, parse_date_range
from euhackscout.models import fold


def _load_cache() -> dict[str, Any]:
    if not APIFY_CACHE_PATH.exists():
        return {}
    try:
        payload = json.loads(APIFY_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _organizer_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return host.split(":")[0] or "Apify"


def item_to_hackathon(item: dict[str, Any]) -> Hackathon | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("title") or item.get("name") or item.get("organicTitle") or "").strip()
    url = str(item.get("url") or item.get("link") or item.get("organicUrl") or "").strip()
    if not name or not url or not url.startswith("http"):
        return None
    snippet = str(item.get("description") or item.get("snippet") or item.get("text") or "")
    blob = f"{name} {snippet}"
    loc = str(item.get("location") or "")
    query = fold(str(item.get("query_id") or item.get("query") or ""))
    if not loc and is_bucharest(blob):
        loc = "Bucharest, Romania"
    elif not loc and ("bucuresti" in query or "bucharest" in query or "romania" in query):
        loc = "Bucharest, Romania"
    fmt = Format.ONLINE if "online" in fold(f"{blob} {loc}") else Format.IN_PERSON
    start = parse_date(item.get("start_date") or item.get("date"))
    deadline = parse_date(item.get("deadline"))
    end = None
    if not (start or deadline):
        start, end = parse_date_range(blob)
    return Hackathon(
        name=name,
        organizer=_organizer_from_url(url),
        url=url,
        source="apify",
        location=loc,
        format=fmt,
        start_date=start,
        end_date=end,
        registration_deadline=deadline,
        tags=("apify",),
    )


def fetch(http: HttpClient) -> list[Hackathon]:  # noqa: ARG001
    payload = _load_cache()
    out: list[Hackathon] = []
    seen: set[str] = set()
    for item in payload.get("items") or []:
        hackathon = item_to_hackathon(item)
        if hackathon is None or hackathon.uid in seen:
            continue
        seen.add(hackathon.uid)
        out.append(hackathon)
    return out
