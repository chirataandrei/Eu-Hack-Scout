"""Apify-powered discovery of Bucharest student-league hackathons.

The daily scan never talks to Apify. ``apify-refresh`` writes
``data/apify_cache.json``; ``sources.apify_scout`` only reads it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from euhackscout.config import (
    APIFY_CACHE_PATH,
    RO_ORGS_PATH,
    apify_actor_crawler,
    apify_actor_discovery,
)
from euhackscout.net.apify import ApifyClient, ApifyState, guarded_run

GOOGLE_QUERIES = [
    "hackathon București 2026",
    'HackITAll OR BESTEM OR "Electron Hackathon" OR "EESTEC Olympics"',
    'Smarthack OR "GitGood Hack" OR "24 Hours of Google" București',
    '"Innovation Labs" hackathon 2026',
    '"NASA Space Apps" București',
    '"CAD&CRAFT" OR OSFIIR hackathon București',
    "site:lsacbucuresti.ro OR site:bestbucharest.ro OR site:asmi.ro hackathon",
    "site:lsebucuresti.org OR site:eestec.ro hackathon",
    "site:linkedin.com/posts hackathon București 2026",
    "site:lablab.ai hackathon",
    "site:hackathon.com bucharest OR romania",
]

GOOGLE_COST_PER_PAGE = 0.0045
GOOGLE_PAGES = 2
CRAWLER_COST_USD = 0.05


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def discovery_input() -> dict[str, Any]:
    return {
        "queries": "\n".join(GOOGLE_QUERIES),
        "maxPagesPerQuery": GOOGLE_PAGES,
        "resultsPerPage": 10,
        "mobileResults": False,
        "languageCode": "en",
    }


def estimated_discovery_cost() -> float:
    return len(GOOGLE_QUERIES) * GOOGLE_PAGES * GOOGLE_COST_PER_PAGE + 0.001


SPA_EXTRA = [
    "https://lsebucuresti.org/",
    "https://eestec.ro/",
    "https://lablab.ai/event",
    "https://hackathon.com/city/romania/bucharest",
]


def spa_urls() -> list[str]:
    raw = _load_json(RO_ORGS_PATH, {"orgs": []})
    orgs = raw.get("orgs") if isinstance(raw, dict) else raw
    urls: list[str] = []
    seen: set[str] = set()
    for org in orgs or []:
        if not isinstance(org, dict):
            continue
        if str(org.get("engine") or "") != "html":
            continue
        homepage = str(org.get("homepage") or "")
        if homepage:
            urls.append(homepage)
        for extra in org.get("event_urls") or []:
            if extra:
                urls.append(str(extra))
    urls.extend(SPA_EXTRA)
    out: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def crawler_input() -> dict[str, Any]:
    return {
        "startUrls": [{"url": url} for url in spa_urls()],
        "maxCrawlPages": 20,
        "maxCrawlDepth": 1,
        "crawlerType": "cheerio",
    }


def _query_term(item: dict[str, Any]) -> str:
    """The actor batches all GOOGLE_QUERIES into one run; searchQuery.term is the
    only way to know which literal query string produced a given result row."""
    search_query = item.get("searchQuery")
    if isinstance(search_query, dict):
        term = search_query.get("term")
        if isinstance(term, str) and term.strip():
            return term
    return "google"


def _urls_from_serp_item(item: dict[str, Any], query_id: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    query_id = query_id or _query_term(item)
    title = str(item.get("title") or item.get("organicTitle") or "")
    snippet = str(item.get("description") or item.get("snippet") or "")
    for key in ("url", "link", "organicUrl", "displayedUrl"):
        value = item.get(key)
        if isinstance(value, str) and value.startswith("http"):
            rows.append({"title": title, "url": value, "description": snippet, "query_id": query_id})
    organic = item.get("organicResults") or item.get("organic") or []
    if isinstance(organic, list):
        for row in organic:
            if isinstance(row, dict):
                rows.extend(_urls_from_serp_item(row, query_id=query_id))
    return rows


def _cache_payload(items: list[dict[str, Any]], query_id: str) -> dict[str, Any]:
    existing = _load_json(APIFY_CACHE_PATH, {"items": []})
    if not isinstance(existing, dict):
        existing = {"items": []}
    previous = [x for x in (existing.get("items") or []) if isinstance(x, dict) and x.get("query_id") != query_id]
    stamped = []
    for item in items:
        row = dict(item)
        row.setdefault("query_id", query_id)
        stamped.append(row)
    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": previous + stamped,
    }


def run_google(*, dry_run: bool = False, client: ApifyClient | None = None, check_cooldown: bool = True) -> list[dict[str, Any]]:
    payload = discovery_input()
    cost = estimated_discovery_cost()
    if dry_run:
        print(f"· google dry-run  actor={apify_actor_discovery()}  cost≈${cost:.3f}")
        print(f"  queries={len(GOOGLE_QUERIES)}  pages/query={GOOGLE_PAGES}")
        return []
    items = guarded_run(
        apify_actor_discovery(),
        payload,
        estimated_cost_usd=cost,
        limit=200,
        client=client,
        check_cooldown=check_cooldown,
    )
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.extend(_urls_from_serp_item(item))
        if item.get("url") or item.get("title"):
            row = dict(item)
            row["query_id"] = _query_term(item)
            rows.append(row)
    cache = _cache_payload(rows, "google")
    APIFY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    APIFY_CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    print(f"· google: {len(rows)} rows → {APIFY_CACHE_PATH}")
    return rows


def run_crawler(*, dry_run: bool = False, client: ApifyClient | None = None, check_cooldown: bool = True) -> list[dict[str, Any]]:
    payload = crawler_input()
    if dry_run:
        print(f"· crawler dry-run  actor={apify_actor_crawler()}  urls={len(payload['startUrls'])}")
        return []
    if not payload["startUrls"]:
        return []
    items = guarded_run(
        apify_actor_crawler(),
        payload,
        estimated_cost_usd=CRAWLER_COST_USD,
        limit=50,
        client=client,
        check_cooldown=check_cooldown,
    )
    stamped = []
    for item in items:
        row = dict(item)
        row["query_id"] = "crawler"
        if not row.get("title"):
            row["title"] = str(row.get("metadata", {}).get("title") or "") if isinstance(row.get("metadata"), dict) else ""
        if not row.get("url"):
            row["url"] = str(row.get("loadedUrl") or row.get("crawl", {}).get("loadedUrl") or "")
        stamped.append(row)
    cache = _cache_payload(stamped, "crawler")
    APIFY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    APIFY_CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")
    print(f"· crawler: {len(stamped)} rows → {APIFY_CACHE_PATH}")
    return stamped


def apify_refresh(*, dry_run: bool = False, force: bool = False) -> int:
    client = ApifyClient()
    if not client.enabled and not dry_run:
        print("· apify-refresh: APIFY_TOKEN not set, nothing to do")
        return 0
    state = ApifyState.load()
    ok, reason = state.can_run(check_cooldown=not force)
    if not ok and not dry_run:
        print(f"· apify-refresh: skipping — {reason}")
        return 0
    print(
        f"· apify budget  month={state.month}  spent=${state.spent_usd:.2f}  "
        f"remaining=${state.remaining_budget():.2f}  runs={state.runs}"
    )
    run_google(dry_run=dry_run, client=client, check_cooldown=not force)
    run_crawler(dry_run=dry_run, client=client, check_cooldown=False)
    return 0
