"""Fetch + filter + dedupe every source into three on-disk shards."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from euhackscout.config import BUCHAREST_PATH, COVERAGE_PATH, EUROPE_PATH, ONLINE_PATH
from euhackscout.filters import effective_deadline, is_bucharest, is_online, keep_hackathon
from euhackscout.http import HttpClient
from euhackscout.models import Hackathon
from euhackscout.net.pool import make_shared_http_client, run_parallel, safe_print
from euhackscout.sources.base import SourceSpec
from euhackscout.sources.registry import SOURCES
from euhackscout.store import fingerprint


def _fetch_source(spec: SourceSpec, http: HttpClient) -> tuple[list[Hackathon], dict]:
    try:
        raw = spec.fetch(http)
    except Exception as exc:  # noqa: BLE001 — one bad source must not abort the scan
        safe_print(f"! {spec.label}: {exc}")
        return [], {"name": spec.label, "source": spec.source, "raw": 0, "kept": 0, "error": str(exc)}
    kept: list[Hackathon] = []
    for item in raw:
        if keep_hackathon(
            item,
            require_keyword=spec.require_keyword,
            assume_bucharest=spec.assume_bucharest,
        ):
            kept.append(item)
    safe_print(f"· {spec.label:28} {spec.source:16} raw={len(raw):4} kept={len(kept):3}")
    return kept, {"name": spec.label, "source": spec.source, "raw": len(raw), "kept": len(kept)}


def _write_coverage(rows: list[dict]) -> None:
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sources": rows,
    }
    COVERAGE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def dedupe(items: list[Hackathon]) -> list[Hackathon]:
    seen_uid: set[str] = set()
    seen_fp: set[str] = set()
    out: list[Hackathon] = []
    for item in items:
        if item.uid in seen_uid:
            continue
        fp = fingerprint(item)
        if fp in seen_fp:
            continue
        seen_uid.add(item.uid)
        seen_fp.add(fp)
        out.append(item)
    return out


def route_bucket(item: Hackathon) -> str:
    if is_online(item.format):
        return "online"
    loc = item.location
    if is_bucharest(loc):
        return "bucharest"
    return "europe"


def _sort_key(item: Hackathon) -> tuple:
    deadline = effective_deadline(item)
    return (deadline is None, deadline or datetime.max.date(), item.name.lower())


def write_shards(items: list[Hackathon]) -> dict[str, list[Hackathon]]:
    buckets = {"bucharest": [], "europe": [], "online": []}
    for item in items:
        buckets[route_bucket(item)].append(item)
    stamp = datetime.now(timezone.utc).isoformat()
    paths = {"bucharest": BUCHAREST_PATH, "europe": EUROPE_PATH, "online": ONLINE_PATH}
    for name, rows in buckets.items():
        rows.sort(key=_sort_key)
        paths[name].parent.mkdir(parents=True, exist_ok=True)
        paths[name].write_text(
            json.dumps(
                {"updated_at": stamp, "hackathons": [h.to_dict() for h in rows]},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    return buckets


def scan(http: HttpClient | None = None) -> list[Hackathon]:
    http = http or make_shared_http_client()
    results = run_parallel(SOURCES, lambda spec: _fetch_source(spec, http))
    collected: list[Hackathon] = []
    coverage: list[dict] = []
    for items, stats in results:
        collected.extend(items)
        coverage.append(stats)
    _write_coverage(coverage)
    unique = dedupe(collected)
    write_shards(unique)
    return unique
