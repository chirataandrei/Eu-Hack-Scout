"""Per-host throttling so a thread pool can fetch many sources concurrently
without hammering any single host faster than REQUEST_GAP_SECONDS.
"""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse


class HostRateLimiter:
    def __init__(self, gap: float) -> None:
        self.gap = gap
        self._registry_lock = threading.Lock()
        self._host_locks: dict[str, threading.Lock] = {}
        self._last_at: dict[str, float] = {}

    def _lock_for(self, host: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._host_locks.get(host)
            if lock is None:
                lock = threading.Lock()
                self._host_locks[host] = lock
            return lock

    def wait(self, url: str) -> None:
        if self.gap <= 0:
            return
        host = (urlparse(url).netloc or url).lower()
        lock = self._lock_for(host)
        with lock:
            last = self._last_at.get(host, 0.0)
            remaining = self.gap - (time.monotonic() - last)
            if remaining > 0:
                time.sleep(remaining)
            self._last_at[host] = time.monotonic()
