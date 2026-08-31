from __future__ import annotations

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

URL = "https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons&per_page=50&page={page}"


def _location(raw: dict) -> str:
    locs = raw.get("locations") or []
    parts: list[str] = []
    if isinstance(locs, list):
        for loc in locs:
            if isinstance(loc, dict):
                parts.append(str(loc.get("name") or loc.get("city") or ""))
            else:
                parts.append(str(loc))
    addr = raw.get("address_with_country_logo")
    if isinstance(addr, dict):
        parts.append(str(addr.get("name") or addr.get("city") or ""))
    return ", ".join(p for p in parts if p) or str(raw.get("region") or "")


def fetch(http: HttpClient) -> list[Hackathon]:
    out: list[Hackathon] = []
    seen: set[str] = set()
    for page in range(1, 4):
        status, data = http.get_json(URL.format(page=page))
        if status != 200 or not isinstance(data, dict):
            break
        rows = ((data.get("data") or {}).get("data")) or []
        if not rows:
            break
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("title") or "").strip()
            public = str(raw.get("public_url") or raw.get("seo_url") or "").strip()
            url = public if public.startswith("http") else f"https://unstop.com/{public.lstrip('/')}"
            if not name or not public or url in seen:
                continue
            seen.add(url)
            region = str(raw.get("region") or "").lower()
            subtype = str(raw.get("subtype") or "").lower()
            if "online" in subtype or region in {"online", "virtual"}:
                fmt = Format.ONLINE
            else:
                fmt = Format.IN_PERSON
            org = raw.get("organisation") or {}
            organizer = str(org.get("name") or "Unstop") if isinstance(org, dict) else "Unstop"
            out.append(
                Hackathon(
                    name=name,
                    organizer=organizer,
                    url=url,
                    source="unstop",
                    location=_location(raw),
                    format=fmt,
                    end_date=parse_date(raw.get("end_date")),
                    registration_deadline=parse_date(raw.get("end_date")),
                    tags=tuple(str(t) for t in (raw.get("tags") or []) if t),
                )
            )
    return out
