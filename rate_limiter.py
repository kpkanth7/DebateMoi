"""
DebateMoi — In-Memory Rate Limiter
====================================
Threading-safe, in-memory daily rate limiter.
Persists for the lifetime of the running Streamlit process (survives reruns,
resets if the server restarts — acceptable for a demo).
"""

import threading
from datetime import datetime, timezone


class RateLimiter:
    MAX_DEBATES_PER_DAY = 3

    def __init__(self):
        self._lock = threading.Lock()
        # {identifier: {date_str: count}}
        self._data: dict[str, dict[str, int]] = {}

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_count(self, identifier: str) -> int:
        return self._data.get(identifier, {}).get(self._today(), 0)

    def get_remaining(self, identifier: str) -> int:
        return max(0, self.MAX_DEBATES_PER_DAY - self.get_count(identifier))

    def check_and_increment(self, identifier: str) -> bool:
        """Atomically check limit and increment. Returns True if allowed."""
        with self._lock:
            today = self._today()
            count = self._data.get(identifier, {}).get(today, 0)
            if count >= self.MAX_DEBATES_PER_DAY:
                return False
            if identifier not in self._data:
                self._data[identifier] = {}
            self._data[identifier][today] = count + 1
            return True
