"""Paths, .env loading, and tunable thresholds."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

SEEN_PATH = DATA_DIR / "seen.json"
COVERAGE_PATH = DATA_DIR / "coverage.json"
RO_ORGS_PATH = DATA_DIR / "ro_orgs.json"

BUCHAREST_PATH = DATA_DIR / "bucharest.json"
EUROPE_PATH = DATA_DIR / "europe.json"
ONLINE_PATH = DATA_DIR / "online.json"

APIFY_CACHE_PATH = DATA_DIR / "apify_cache.json"
APIFY_STATE_PATH = DATA_DIR / "apify_state.json"
APIFY_QUERIES_PATH = DATA_DIR / "apify_queries.json"

ENV_PATH = ROOT / ".env"


def load_dotenv(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except (TypeError, ValueError):
        return default


def apify_token() -> str:
    return (os.environ.get("APIFY_TOKEN") or "").strip()


def apify_max_spend_per_month() -> float:
    return _env_float("APIFY_MAX_SPEND_PER_MONTH", 4.20)


def apify_max_runs_per_month() -> int:
    return _env_int("APIFY_MAX_RUNS_PER_MONTH", 90)


def apify_min_hours_between_runs() -> float:
    return _env_float("APIFY_MIN_HOURS_BETWEEN_RUNS", 6.0)


def apify_actor_discovery() -> str:
    return os.environ.get("APIFY_ACTOR_DISCOVERY") or "apify/google-search-scraper"


def apify_actor_crawler() -> str:
    return os.environ.get("APIFY_ACTOR_CRAWLER") or "apify/website-content-crawler"


def http_max_workers() -> int:
    return _env_int("EUHACKSCOUT_MAX_WORKERS", 8)


def http_request_gap_seconds() -> float:
    return _env_float("EUHACKSCOUT_REQUEST_GAP_SECONDS", 0.35)
