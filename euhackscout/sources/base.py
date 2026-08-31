"""Shared shape for hackathon sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from euhackscout.http import HttpClient
from euhackscout.models import Hackathon


@dataclass(frozen=True)
class SourceSpec:
    label: str
    source: str
    fetch: Callable[[HttpClient], list[Hackathon]]
    assume_bucharest: bool = False
    require_keyword: bool = False
