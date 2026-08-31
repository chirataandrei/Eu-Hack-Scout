from __future__ import annotations

import json
import re
from typing import Any

from euhackscout.filters import is_europe
from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date

SEARCH_URL = "https://gdg.community.dev/api/search/?result_types=upcoming_event&query=hackathon"
CHAPTER_URLS = (
    "https://gdg.community.dev/gdg-bucharest/",
    "https://gdg.community.dev/gdg-cloud-bucharest/",
    "https://gdg.community.dev/gdg-cluj/",
    "https://gdg.community.dev/gdg-iasi/",
    "https://gdg.community.dev/gdg-timisoara/",
)
NEXT_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
EU_CC = {
    "RO", "DE", "FR", "NL", "PL", "ES", "IT", "GB", "UK", "PT", "SE", "AT", "BE",
    "IE", "DK", "FI", "NO", "CH", "CZ", "HU", "GR", "BG", "HR", "SK", "SI", "LT",
    "LV", "EE", "LU", "MT", "CY",
}


def _walk_events(node: Any, found: list[dict[str, Any]]) -> None:
    if isinstance(node, dict):
        if node.get("title") and node.get("url") and (
            "/events/" in str(node.get("url")) or node.get("start_date")
        ):
            found.append(node)
        for value in node.values():
            _walk_events(value, found)
    elif isinstance(node, list):
        for item in node:
            _walk_events(item, found)


def _from_row(row: dict[str, Any], *, default_loc: str = "") -> Hackathon | None:
    name = str(row.get("title") or row.get("name") or "").strip()
    url = str(row.get("url") or row.get("event_url") or "").strip()
    if url and not url.startswith("http"):
        url = f"https://gdg.community.dev{url}"
    if not name or not url:
        return None
    chapter = row.get("chapter") if isinstance(row.get("chapter"), dict) else {}
    loc_parts = [
        str(row.get("city") or chapter.get("city") or ""),
        str(chapter.get("country_name") or chapter.get("country") or ""),
    ]
    loc = ", ".join(p for p in loc_parts if p) or default_loc
    cc = str(chapter.get("country") or "").upper()
    is_online = bool(row.get("is_virtual") or row.get("online"))
    if not is_online:
        if cc and cc not in EU_CC:
            return None
        if loc and not is_europe(loc) and cc not in EU_CC:
            return None
        if not loc:
            return None
    return Hackathon(
        name=name,
        organizer=str(chapter.get("title") or row.get("chapter_title") or "GDG"),
        url=url,
        source="gdg",
        location=loc,
        format=Format.ONLINE if is_online else Format.IN_PERSON,
        start_date=parse_date(row.get("start_date") or row.get("start_date_iso")),
        end_date=parse_date(row.get("end_date") or row.get("end_date_iso")),
    )


def _from_chapter_page(body: str, *, default_loc: str) -> list[Hackathon]:
    match = NEXT_RE.search(body or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    raw: list[dict[str, Any]] = []
    _walk_events((data.get("props") or {}).get("pageProps") or {}, raw)
    chapter = ((data.get("props") or {}).get("pageProps") or {}).get("chapterData") or {}
    organizer = str(chapter.get("title") or "GDG") if isinstance(chapter, dict) else "GDG"
    out: list[Hackathon] = []
    seen: set[str] = set()
    for row in raw:
        item = _from_row(row, default_loc=default_loc)
        if item is None or item.url in seen:
            continue
        seen.add(item.url)
        out.append(
            Hackathon(
                name=item.name,
                organizer=organizer,
                url=item.url,
                source="gdg",
                location=item.location or default_loc,
                format=item.format,
                start_date=item.start_date,
                end_date=item.end_date,
            )
        )
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    out: list[Hackathon] = []
    seen: set[str] = set()
    status, data = http.get_json(SEARCH_URL)
    if status == 200 and isinstance(data, dict):
        for row in data.get("results") or []:
            if not isinstance(row, dict):
                continue
            item = _from_row(row)
            if item is None or item.url in seen:
                continue
            seen.add(item.url)
            out.append(item)
    for url in CHAPTER_URLS:
        status, body = http.get(url, headers={"Accept": "text/html"})
        if status != 200 or not body:
            continue
        loc = "Bucharest, Romania" if "bucharest" in url else ""
        if "cluj" in url:
            loc = "Cluj-Napoca, Romania"
        elif "iasi" in url:
            loc = "Iași, Romania"
        elif "timisoara" in url:
            loc = "Timișoara, Romania"
        for item in _from_chapter_page(body, default_loc=loc):
            if item.url in seen:
                continue
            seen.add(item.url)
            out.append(item)
    return out
