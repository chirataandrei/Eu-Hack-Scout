from __future__ import annotations

import re
from html import unescape
from xml.etree import ElementTree

from euhackscout.http import HttpClient
from euhackscout.models import Format, Hackathon, parse_date, parse_date_range

TAG_RE = re.compile(r"<[^>]+>")


def _text(node: ElementTree.Element | None) -> str:
    if node is None or node.text is None:
        return ""
    return unescape(TAG_RE.sub(" ", node.text)).strip()


def parse_rss(body: str) -> list[dict[str, str]]:
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return []
    items: list[dict[str, str]] = []
    for item in root.iter():
        tag = item.tag.rsplit("}", 1)[-1].lower()
        if tag != "item":
            continue
        fields: dict[str, str] = {}
        for child in item:
            ctag = child.tag.rsplit("}", 1)[-1].lower()
            if ctag in {"title", "link", "description", "pubdate", "guid"}:
                fields[ctag] = _text(child)
        if fields.get("title") and fields.get("link"):
            items.append(fields)
    return items


def fetch_rss(
    http: HttpClient,
    feed_url: str,
    *,
    organizer: str,
    source: str,
    assume_bucharest: bool,
    location: str = "",
) -> list[Hackathon]:
    status, body = http.get(feed_url, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
    if status != 200 or not body:
        return []
    out: list[Hackathon] = []
    for item in parse_rss(body):
        title = item["title"]
        blob = f"{title} {item.get('description') or ''}"
        start, end = parse_date_range(blob)
        out.append(
            Hackathon(
                name=title,
                organizer=organizer,
                url=item["link"],
                source=source,
                location=location or ("Bucharest, Romania" if assume_bucharest else "Romania"),
                format=Format.IN_PERSON if (assume_bucharest or location) else Format.ONLINE,
                start_date=start,
                end_date=end,
                registration_deadline=parse_date(item.get("pubdate")),
            )
        )
    return out
