from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

QUERIES = ("hackathon", "datathon", "hack", "hackathon bucharest", "hackathon romania")
ENDPOINT = "https://api.lu.ma/discover/get-paginated-events"


def _format(location_type: str) -> Format:
    kind = (location_type or "").lower()
    if kind in {"online", "virtual"}:
        return Format.ONLINE
    if kind in {"hybrid"}:
        return Format.HYBRID
    return Format.IN_PERSON


def _location(event: dict) -> str:
    geo = event.get("geo_address_info") or {}
    parts = [str(geo.get("city") or ""), str(geo.get("city_state") or ""), str(geo.get("country") or "")]
    loc = ", ".join(p for p in parts if p)
    return loc or str(geo.get("region") or "")


def fetch(http: HttpClient) -> list[Hackathon]:
    seen: set[str] = set()
    out: list[Hackathon] = []
    for query in QUERIES:
        url = f"{ENDPOINT}?period=future&pagination_limit=50&query={query.replace(' ', '%20')}"
        status, data = http.get_json(url)
        if status != 200 or not isinstance(data, dict):
            continue
        for row in data.get("entries") or []:
            event = (row or {}).get("event") if isinstance(row, dict) else None
            if not isinstance(event, dict):
                continue
            name = str(event.get("name") or "").strip()
            event_url = str(event.get("url") or "").strip()
            if event_url and not event_url.startswith("http"):
                event_url = f"https://lu.ma/{event_url.lstrip('/')}"
            if not name or not event_url or event_url in seen:
                continue
            seen.add(event_url)
            cal = event.get("calendar") if isinstance(event.get("calendar"), dict) else {}
            organizer = str(cal.get("name") or event.get("user_api_id") or "Luma")
            if organizer.startswith("usr-") or not organizer.strip():
                organizer = "Luma"
            out.append(
                Hackathon(
                    name=name,
                    organizer=organizer,
                    url=event_url,
                    source="luma",
                    location=_location(event),
                    format=_format(str(event.get("location_type") or "")),
                    start_date=parse_date(event.get("start_at")),
                    end_date=parse_date(event.get("end_at")),
                )
            )
    return out
