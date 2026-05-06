"""
DebateMoi — Rate Limiter
=========================
Two-layer: in-memory dict (fast) + SQLite at /tmp (survives app sleep/wake).
Limits each identifier to 3 debates per UTC calendar day.
"""

import sqlite3
import threading
from datetime import datetime, timezone

_DB_PATH = "/tmp/debatemoi_rl.db"


class RateLimiter:
    MAX_DEBATES_PER_DAY = 3

    def __init__(self):
        self._lock = threading.Lock()
        self._cache: dict[str, dict[str, int]] = {}
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS limits (
                    identifier TEXT NOT NULL,
                    date       TEXT NOT NULL,
                    count      INTEGER DEFAULT 0,
                    PRIMARY KEY (identifier, date)
                )
            """)
            # Clean up entries older than 7 days
            conn.execute(
                "DELETE FROM limits WHERE date < date('now', '-7 days')"
            )

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _db_count(self, identifier: str, today: str) -> int:
        try:
            with sqlite3.connect(_DB_PATH) as conn:
                row = conn.execute(
                    "SELECT count FROM limits WHERE identifier=? AND date=?",
                    (identifier, today),
                ).fetchone()
                return row[0] if row else 0
        except Exception:
            return 0

    def get_count(self, identifier: str) -> int:
        today = self._today()
        cached = self._cache.get(identifier, {}).get(today)
        if cached is not None:
            return cached
        count = self._db_count(identifier, today)
        self._cache.setdefault(identifier, {})[today] = count
        return count

    def get_remaining(self, identifier: str) -> int:
        return max(0, self.MAX_DEBATES_PER_DAY - self.get_count(identifier))

    def check_and_increment(self, identifier: str) -> bool:
        """Atomically check + increment. Returns True if debate is allowed."""
        today = self._today()
        with self._lock:
            # Refresh from DB if not in cache (handles app-restart scenario)
            if identifier not in self._cache or today not in self._cache.get(identifier, {}):
                count = self._db_count(identifier, today)
                self._cache.setdefault(identifier, {})[today] = count

            count = self._cache[identifier][today]
            if count >= self.MAX_DEBATES_PER_DAY:
                return False

            # Increment in memory
            self._cache[identifier][today] = count + 1

            # Write-through to SQLite
            try:
                with sqlite3.connect(_DB_PATH) as conn:
                    conn.execute("""
                        INSERT INTO limits (identifier, date, count) VALUES (?, ?, 1)
                        ON CONFLICT(identifier, date) DO UPDATE SET count = count + 1
                    """, (identifier, today))
            except Exception:
                pass  # Memory already updated; SQLite failure is non-fatal for demo

            return True
