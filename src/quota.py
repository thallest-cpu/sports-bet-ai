"""Process-safe local quota reservations; survives reruns/restarts on same disk.

Provider headers/errors remain authoritative. This guard is per deployment,
not an account-wide accounting service and not a durable prediction store.
"""
from contextlib import contextmanager
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path


class QuotaGuard:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS budget (key TEXT PRIMARY KEY, day TEXT, used INTEGER, blocked_until REAL, reason TEXT)')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            with db:
                yield db
        finally:
            db.close()

    def reserve(self, key, limit):
        today = datetime.now(timezone.utc).date().isoformat()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT day, used, blocked_until, reason FROM budget WHERE key=?', (key,)).fetchone()
            if row and row[2] > time.time():
                return False, row[3]
            used = row[1] if row and row[0] == today else 0
            if used >= limit:
                return False, 'Cota local de proteção esgotada; nova janela às 00:00 UTC.'
            db.execute('INSERT OR REPLACE INTO budget VALUES (?, ?, ?, 0, ?)', (key, today, used + 1, ''))
            return True, ''

    def block(self, key, seconds, reason):
        with self.connection() as db:
            db.execute('UPDATE budget SET blocked_until=?, reason=? WHERE key=?', (time.time() + seconds, reason, key))
