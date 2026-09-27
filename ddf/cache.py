import json
import sqlite3
import threading
import time
from pathlib import Path


class Cache:
    """Tiny SQLite key-value store so prices are fetched once a day, not on every search."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()  # availability checks run in a thread pool
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT, stored_at REAL)")

    def get(self, key: str, max_age_seconds: float):
        with self._lock:
            row = self._db.execute("SELECT value, stored_at FROM kv WHERE key = ?", (key,)).fetchone()
        if row is None or time.time() - row[1] > max_age_seconds:
            return None
        return json.loads(row[0])

    def put(self, key: str, value) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO kv (key, value, stored_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()),
            )
            self._db.commit()
