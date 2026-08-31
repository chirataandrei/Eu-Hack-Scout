from __future__ import annotations

from html import unescape
import re
from typing import Any

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date_range
from euhackscout.sources.engines.jsonld import events_from_html

OG_TITLE_RE = re.compile(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(_strip_html(text))).strip()


def posts_from_wordpress(http: HttpClient, base_url: str, *, search: str = "hack") -> list[dict[str, Any]]:
    root = base_url.rstrip("/")
    url = f"{root}/wp-json/wp/v2/posts?search={search}&per_page=20"
    status, data = http.get_json(url)
    if status != 200 or not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def hackathons_from_wp_posts(
    posts: list[dict[str, Any]],
    *,
    organizer: str,
    source: str,
    assume_bucharest: bool,
    location: str = "",
) -> list[Hackathon]:
    out: list[Hackathon] = []
    fallback = location or ("Bucharest, Romania" if assume_bucharest else "")
    for raw in posts:
        title = _clean(str((raw.get("title") or {}).get("rendered") or raw.get("slug") or ""))
        link = str(raw.get("link") or "").strip()
        if not title or not link:
            continue
        content = _clean(
            str((raw.get("content") or {}).get("rendered") or (raw.get("excerpt") or {}).get("rendered") or "")
        )
        start, end = parse_date_range(f"{title} {content}")
        loc = fallback or ("Bucharest, Romania" if assume_bucharest else "")
        out.append(
            Hackathon(
                name=title,
                organizer=organizer,
                url=link,
                source=source,
                location=loc,
                format=Format.IN_PERSON if (assume_bucharest or fallback) else Format.ONLINE,
                start_date=start,
                end_date=end,
                tags=("romania",),
            )
        )
    return out


def hackathons_from_html(
    html: str,
    *,
    url: str,
    organizer: str,
    source: str,
    assume_bucharest: bool,
    location: str = "",
) -> list[Hackathon]:
    events = events_from_html(html, page_url=url)
    fallback = location or ("Bucharest, Romania" if assume_bucharest else "")
    if events:
        out: list[Hackathon] = []
        for event in events:
            loc = event.get("location") or fallback
            fmt = event.get("format") or (Format.IN_PERSON if (assume_bucharest or fallback) else Format.ONLINE)
            out.append(
                Hackathon(
                    name=event["name"],
                    organizer=organizer,
                    url=event.get("url") or url,
                    source=source,
                    location=loc,
                    format=fmt,
                    start_date=event.get("start_date"),
                    end_date=event.get("end_date"),
                    registration_deadline=event.get("registration_deadline"),
                )
            )
        return out
    title = ""
    og = OG_TITLE_RE.search(html)
    if og:
        title = _clean(og.group(1))
    if not title:
        match = TITLE_RE.search(html)
        title = _clean(match.group(1)) if match else ""
    if not title:
        return []
    start, end = parse_date_range(_clean(html[:8000]))
    return [
        Hackathon(
            name=title,
            organizer=organizer,
            url=url,
            source=source,
            location=fallback,
            format=Format.IN_PERSON if (assume_bucharest or fallback) else Format.ONLINE,
            start_date=start,
            end_date=end,
        )
    ]
