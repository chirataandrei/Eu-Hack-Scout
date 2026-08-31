from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from euhackscout.models import Format, parse_date

LD_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _location_from(node: dict[str, Any]) -> str:
    loc = node.get("location")
    if isinstance(loc, str):
        return loc.strip()
    if isinstance(loc, dict):
        name = str(loc.get("name") or "")
        addr = loc.get("address")
        if isinstance(addr, dict):
            parts = [
                str(addr.get("addressLocality") or ""),
                str(addr.get("addressRegion") or ""),
                str(addr.get("addressCountry") or ""),
            ]
            joined = ", ".join(p for p in parts if p)
            return joined or name
        if isinstance(addr, str):
            return addr
        return name
    return ""


def _format_from(node: dict[str, Any]) -> Format:
    mode = str(node.get("eventAttendanceMode") or "").lower()
    if "online" in mode and "offline" in mode:
        return Format.HYBRID
    if "online" in mode:
        return Format.ONLINE
    if "offline" in mode or "place" in str(node.get("location") or "").lower():
        return Format.IN_PERSON
    loc = _location_from(node).lower()
    if "online" in loc or "virtual" in loc or "remote" in loc:
        return Format.ONLINE
    if loc:
        return Format.IN_PERSON
    return Format.ONLINE


def _walk(node: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if isinstance(node, list):
        for item in node:
            events.extend(_walk(item))
        return events
    if not isinstance(node, dict):
        return events
    types = {str(t).lower() for t in _as_list(node.get("@type"))}
    if "event" in types:
        events.append(node)
    for key in ("itemListElement", "item", "events", "@graph"):
        if key in node:
            events.extend(_walk(node[key]))
    return events


def parse_ldjson(blob: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return []
    return _walk(data)


def events_from_html(html: str, *, page_url: str = "") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for blob in LD_RE.findall(html or ""):
        for node in parse_ldjson(blob):
            name = str(node.get("name") or "").strip()
            if not name:
                continue
            url = str(node.get("url") or page_url).strip()
            if url and not url.startswith("http") and page_url:
                url = urljoin(page_url, url)
            loc = _location_from(node)
            out.append(
                {
                    "name": name,
                    "url": url,
                    "location": loc,
                    "format": _format_from(node),
                    "start_date": parse_date(node.get("startDate")),
                    "end_date": parse_date(node.get("endDate")),
                    "registration_deadline": parse_date(
                        node.get("offers", {}).get("validThrough") if isinstance(node.get("offers"), dict) else None
                    ),
                    "organizer": (
                        str((node.get("organizer") or {}).get("name") or "")
                        if isinstance(node.get("organizer"), dict)
                        else str(node.get("organizer") or "")
                    ),
                }
            )
    return out
