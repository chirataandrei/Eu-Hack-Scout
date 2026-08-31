"""Shim — HttpClient lives in euhackscout.net.http."""

from __future__ import annotations

from euhackscout.net.http import DEFAULT_TIMEOUT, REQUEST_GAP_SECONDS, USER_AGENT, HttpClient

__all__ = ["DEFAULT_TIMEOUT", "REQUEST_GAP_SECONDS", "USER_AGENT", "HttpClient"]
