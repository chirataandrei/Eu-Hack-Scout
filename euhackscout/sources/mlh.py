from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

INERTIA_RE = re.compile(r'<script data-page="app" type="application/json">(.*?)</script>', re.S)
EU_COUNTRIES = {
    "GB", "UK", "IE", "DE", "FR", "NL", "BE", "AT", "CH", "PL", "CZ", "HU", "SE", "DK",
    "NO", "FI", "ES", "PT", "IT", "GR", "BG", "HR", "SK", "SI", "LT", "LV", "EE", "LU",
    "MT", "CY", "RO", "RS", "MD", "UA",
}


def current_season(today: date | None = None) -> int:
    today = today or date.today()
    # MLH seasons run July–June; July 2026 starts season 2027.
    return today.year + 1 if today.month >= 7 else today.year


def _format(value: str) -> Format:
    kind = (value or "").lower()
    if kind in {"digital", "online", "virtual"}:
        return Format.ONLINE
    if kind == "hybrid":
        return Format.HYBRID
    return Format.IN_PERSON


def _location(event: dict[str, Any]) -> str:
    venue = event.get("venueAddress") or {}
    loc_parts = [
        str(event.get("location") or ""),
        str(venue.get("city") or "") if isinstance(venue, dict) else "",
        str(venue.get("country") or "") if isinstance(venue, dict) else "",
    ]
    return ", ".join(p for p in loc_parts if p)


def _keep_mlh(event: dict[str, Any], fmt: Format) -> bool:
    if fmt is Format.ONLINE:
        return True
    region = str(event.get("region") or "").upper()
    if region in {"EMEA", "EU", "EUROPE"}:
        return True
    venue = event.get("venueAddress") or {}
    country = str(venue.get("country") or "").upper() if isinstance(venue, dict) else ""
    return country in EU_COUNTRIES


def hackathons_from_inertia(body: str) -> list[Hackathon]:
    match = INERTIA_RE.search(body or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    upcoming = ((data.get("props") or {}).get("upcomingEvents")) or []
    out: list[Hackathon] = []
    for event in upcoming:
        if not isinstance(event, dict):
            continue
        fmt = _format(str(event.get("formatType") or ""))
        if not _keep_mlh(event, fmt):
            continue
        name = str(event.get("name") or "").strip()
        website = str(event.get("websiteUrl") or "").strip()
        path = str(event.get("url") or "").strip()
        event_url = website or (f"https://mlh.io{path}" if path.startswith("/") else path)
        if not name or not event_url:
            continue
        out.append(
            Hackathon(
                name=name,
                organizer="MLH",
                url=event_url,
                source="mlh",
                location=_location(event),
                format=fmt,
                start_date=parse_date(event.get("startsAt")),
                end_date=parse_date(event.get("endsAt")),
            )
        )
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    season = current_season()
    url = f"https://mlh.io/seasons/{season}/events"
    status, body = http.get(url, headers={"Accept": "text/html"})
    if status != 200 or not body:
        return []
    return hackathons_from_inertia(body)
