"""Apify REST client with a budget guard.

HttpClient does not fit Apify directly:

- ``post_json`` treats any status != 200 as failure, but Apify answers 201
  when a run is created.
- ``DEFAULT_TIMEOUT`` (25s) is far below the ~300s a synchronous actor run
  can take.

So this client never calls the synchronous run endpoint. It starts a run
(accepting 200/201), polls ``GET /v2/actor-runs/{runId}`` on a short
interval up to a hard deadline, then reads the dataset.

Budget guard: state persists in data/apify_state.json. Every check happens
before any network call.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from euhackscout.config import (
    APIFY_STATE_PATH,
    apify_max_runs_per_month,
    apify_max_spend_per_month,
    apify_min_hours_between_runs,
    apify_token,
)
from euhackscout.net.http import HttpClient

API_BASE = "https://api.apify.com/v2"
POLL_INTERVAL_SECONDS = 10
POLL_DEADLINE_SECONDS = 240
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _current_month(now: datetime | None = None) -> str:
    return (now or _now()).strftime("%Y-%m")


@dataclass
class ApifyState:
    month: str
    runs: int = 0
    spent_usd: float = 0.0
    last_run: str = ""

    @classmethod
    def load(cls, path: Path = APIFY_STATE_PATH) -> "ApifyState":
        if not path.exists():
            return cls(month=_current_month())
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls(month=_current_month())
        state = cls(
            month=str(raw.get("month") or _current_month()),
            runs=int(raw.get("runs") or 0),
            spent_usd=float(raw.get("spent_usd") or 0.0),
            last_run=str(raw.get("last_run") or ""),
        )
        return state.rolled_over()

    def rolled_over(self, now: datetime | None = None) -> "ApifyState":
        month = _current_month(now)
        if self.month == month:
            return self
        return ApifyState(month=month, runs=0, spent_usd=0.0, last_run=self.last_run)

    def save(self, path: Path = APIFY_STATE_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "month": self.month,
                    "runs": self.runs,
                    "spent_usd": round(self.spent_usd, 4),
                    "last_run": self.last_run,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def can_run(self, now: datetime | None = None, *, check_cooldown: bool = True) -> tuple[bool, str]:
        state = self.rolled_over(now)
        if state.spent_usd >= apify_max_spend_per_month():
            return False, f"monthly Apify budget spent (${state.spent_usd:.2f} >= ${apify_max_spend_per_month():.2f})"
        if state.runs >= apify_max_runs_per_month():
            return False, f"monthly Apify run cap reached ({state.runs} >= {apify_max_runs_per_month()})"
        if check_cooldown and state.last_run:
            try:
                last = datetime.fromisoformat(state.last_run)
            except ValueError:
                last = None
            if last is not None:
                elapsed_hours = ((now or _now()) - last).total_seconds() / 3600.0
                min_hours = apify_min_hours_between_runs()
                if elapsed_hours < min_hours:
                    return False, f"cooldown active ({elapsed_hours:.1f}h < {min_hours}h since last run)"
        return True, ""

    def remaining_budget(self) -> float:
        return max(0.0, apify_max_spend_per_month() - self.spent_usd)

    def record_run(self, cost_usd: float, now: datetime | None = None) -> None:
        state = self.rolled_over(now)
        state.runs += 1
        state.spent_usd += max(0.0, cost_usd)
        state.last_run = (now or _now()).isoformat()
        self.month, self.runs, self.spent_usd, self.last_run = (
            state.month,
            state.runs,
            state.spent_usd,
            state.last_run,
        )


class ApifyBudgetExceeded(RuntimeError):
    pass


class ApifyClient:
    def __init__(self, token: str = "", http: HttpClient | None = None) -> None:
        self.token = token or apify_token()
        self.http = http or HttpClient()

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def start_run(self, actor: str, input_payload: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{API_BASE}/actors/{actor.replace('/', '~')}/runs"
        status, body = self.http.request(
            url,
            method="POST",
            data=json.dumps(input_payload).encode("utf-8"),
            headers={**self._headers(), "Content-Type": "application/json", "Accept": "application/json"},
        )
        if status not in (200, 201):
            print(f"! apify start_run {actor}: HTTP {status} {body[:200]}")
            return None
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return None
        return payload.get("data")

    def poll_run(self, run_id: str) -> dict[str, Any] | None:
        deadline = time.monotonic() + POLL_DEADLINE_SECONDS
        url = f"{API_BASE}/actor-runs/{run_id}"
        while time.monotonic() < deadline:
            status, data = self.http.get_json(url, headers=self._headers())
            if status == 200 and isinstance(data, dict):
                run = data.get("data") or {}
                if run.get("status") in TERMINAL_STATUSES:
                    return run
            time.sleep(POLL_INTERVAL_SECONDS)
        return None

    def dataset_items(self, dataset_id: str, limit: int = 200) -> list[dict[str, Any]]:
        url = f"{API_BASE}/datasets/{dataset_id}/items?format=json&clean=1&limit={limit}"
        status, data = self.http.get_json(url, headers=self._headers())
        if status != 200 or not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def run_actor_sync(self, actor: str, input_payload: dict[str, Any], *, limit: int = 200) -> list[dict[str, Any]]:
        run = self.start_run(actor, input_payload)
        if not run or not run.get("id"):
            return []
        finished = self.poll_run(str(run["id"]))
        if not finished or finished.get("status") != "SUCCEEDED":
            return []
        dataset_id = finished.get("defaultDatasetId")
        if not dataset_id:
            return []
        return self.dataset_items(str(dataset_id), limit=limit)


def guarded_run(
    actor: str,
    input_payload: dict[str, Any],
    *,
    estimated_cost_usd: float,
    limit: int = 200,
    client: ApifyClient | None = None,
    state_path: Path = APIFY_STATE_PATH,
    check_cooldown: bool = True,
) -> list[dict[str, Any]]:
    """Runs an actor only if the budget guard allows it, then records spend."""
    client = client or ApifyClient()
    if not client.enabled:
        print("· apify: APIFY_TOKEN not set, skipping")
        return []
    state = ApifyState.load(state_path)
    ok, reason = state.can_run(check_cooldown=check_cooldown)
    if not ok:
        print(f"· apify: skipping {actor} — {reason}")
        return []
    items = client.run_actor_sync(actor, input_payload, limit=limit)
    if items:
        state.record_run(estimated_cost_usd)
        state.save(state_path)
    return items
