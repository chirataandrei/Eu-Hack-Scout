"""Romanian student orgs, universities, and press — driven by data/ro_orgs.json."""

from __future__ import annotations

import json
from typing import Any

from euhackscout.config import RO_ORGS_PATH
from euhackscout.filters import is_hackathon
from euhackscout.http import HttpClient
from euhackscout.models import Hackathon
from euhackscout.sources.engines.rss import fetch_rss
from euhackscout.sources.engines.wordpress import hackathons_from_html, hackathons_from_wp_posts, posts_from_wordpress

STRUCTURED_ENGINES = {"wordpress", "html", "jsonld"}


def _load_orgs() -> list[dict[str, Any]]:
    if not RO_ORGS_PATH.exists():
        return []
    try:
        raw = json.loads(RO_ORGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    items = raw.get("orgs") if isinstance(raw, dict) else raw
    return [row for row in (items or []) if isinstance(row, dict)]


def _keep(item: Hackathon) -> bool:
    return is_hackathon(item.name, item.organizer)


def _from_org(http: HttpClient, org: dict[str, Any], *, engines: set[str]) -> list[Hackathon]:
    name = str(org.get("name") or "Unknown")
    source = str(org.get("source") or "ro_orgs")
    assume = bool(org.get("assume_bucharest"))
    default_location = str(org.get("location") or ("Bucharest, Romania" if assume else ""))
    engine = str(org.get("engine") or "html")
    if engine not in engines:
        return []
    homepage = str(org.get("homepage") or "")
    event_urls = [str(u) for u in (org.get("event_urls") or []) if u]
    rows: list[Hackathon] = []
    if engine == "wordpress" and homepage:
        posts = posts_from_wordpress(http, homepage, search=str(org.get("search") or "hack"))
        rows.extend(
            hackathons_from_wp_posts(
                posts,
                organizer=name,
                source=source,
                assume_bucharest=assume,
                location=default_location,
            )
        )
    elif engine == "rss" and homepage:
        rows.extend(
            fetch_rss(
                http,
                homepage,
                organizer=name,
                source=source,
                assume_bucharest=assume,
                location=default_location,
            )
        )
    pages: list[str] = []
    if engine in {"html", "jsonld"}:
        pages = event_urls or ([homepage] if homepage else [])
    elif engine == "wordpress":
        pages = event_urls
    for url in pages:
        status, body = http.get(url, headers={"Accept": "text/html"})
        if status != 200 or not body:
            continue
        rows.extend(
            hackathons_from_html(
                body,
                url=url,
                organizer=name,
                source=source,
                assume_bucharest=assume,
                location=default_location,
            )
        )
    seen: set[str] = set()
    out: list[Hackathon] = []
    for item in rows:
        if item.uid in seen or not _keep(item):
            continue
        seen.add(item.uid)
        out.append(item)
    return out


def fetch(http: HttpClient) -> list[Hackathon]:
    """Student leagues and universities — WP REST + HTML/JSON-LD pages."""
    collected: list[Hackathon] = []
    seen: set[str] = set()
    for org in _load_orgs():
        for item in _from_org(http, org, engines=STRUCTURED_ENGINES):
            if item.uid in seen:
                continue
            seen.add(item.uid)
            collected.append(item)
    return collected


def fetch_press(http: HttpClient) -> list[Hackathon]:
    """Romanian press RSS — last among structured sources, before Apify."""
    collected: list[Hackathon] = []
    seen: set[str] = set()
    for org in _load_orgs():
        for item in _from_org(http, org, engines={"rss"}):
            if item.uid in seen:
                continue
            seen.add(item.uid)
            collected.append(item)
    return collected
