"""
DebateMoi — IP-Based Rate Limiter
==================================
SQLite-backed daily rate limiter that persists across app restarts.
Limits users to 3 debates per calendar day per IP address.
"""

import sqlite3
from datetime import datetime, timezone


class RateLimiter:
    """IP-based daily rate limiter backed by SQLite."""

    MAX_DEBATES_PER_DAY = 3

    def __init__(self, db_path: str = "rate_limits.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Create the rate limits table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                ip_address TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (ip_address, date)
            )
        """)
        self.conn.commit()
        self._cleanup()

    def _cleanup(self):
        """Remove entries older than 7 days to keep the DB small."""
        cutoff = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.conn.execute(
            "DELETE FROM rate_limits WHERE date < date(?, '-7 days')",
            (cutoff,)
        )
        self.conn.commit()

    def _today(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def get_count(self, ip: str) -> int:
        row = self.conn.execute(
            "SELECT count FROM rate_limits WHERE ip_address = ? AND date = ?",
            (ip, self._today())
        ).fetchone()
        return row[0] if row else 0

    def get_remaining(self, ip: str) -> int:
        return max(0, self.MAX_DEBATES_PER_DAY - self.get_count(ip))

    def check_rate_limit(self, ip: str) -> bool:
        return self.get_count(ip) < self.MAX_DEBATES_PER_DAY

    def increment(self, ip: str):
        today = self._today()
        self.conn.execute("""
            INSERT INTO rate_limits (ip_address, date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(ip_address, date)
            DO UPDATE SET count = count + 1
        """, (ip, today))
        self.conn.commit()

    def close(self):
        self.conn.close()
