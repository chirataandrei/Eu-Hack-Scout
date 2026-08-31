from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from euhackscout.config import SEEN_PATH
from euhackscout.models import Hackathon, fold

_WORD_RE = re.compile(r"[a-z0-9]+")
_EDITION_RE = re.compile(
    r"\b(20\d{2}|v(?:ol(?:ume)?)?\.?\s*\d+|season\s*\d+|edition\s*\d+|edi(?:t|ț)ia\s*(?:a\s*)?\w+)\b|#\d+",
    re.I,
)


def load_seen(path: Path = SEEN_PATH) -> set[str]:
    if not path.exists():
        return set()
    raw = json.loads(path.read_text(encoding="utf-8"))
    ids = raw.get("ids") if isinstance(raw, dict) else raw
    if not isinstance(ids, list):
        return set()
    return {str(x) for x in ids}


def save_seen(ids: set[str], path: Path = SEEN_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ids": sorted(ids),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical_name(name: str) -> str:
    folded = fold(name or "")
    folded = _EDITION_RE.sub(" ", folded)
    return " ".join(_WORD_RE.findall(folded))


def fingerprint(hackathon: Hackathon) -> str:
    blob = f"{canonical_name(hackathon.name)}|{hackathon.start_date or ''}"
    return "fp:" + hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def seen_keys_for(items: list[Hackathon]) -> set[str]:
    keys: set[str] = set()
    for item in items:
        keys.add(item.uid)
        keys.add(fingerprint(item))
    return keys


def split_new(items: list[Hackathon], seen: set[str]) -> tuple[list[Hackathon], list[Hackathon]]:
    new, current = [], []
    for item in items:
        current.append(item)
        if item.uid not in seen and fingerprint(item) not in seen:
            new.append(item)
    return new, current
