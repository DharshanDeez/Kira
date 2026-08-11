"""SQLite-backed reminders."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Reminder:
    id: int
    message: str
    due_at: float
    created_at: float
    status: str

    @property
    def due_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.due_at)


class ReminderStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    due_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    fired_at REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(status, due_at)"
            )

    def create(self, message: str, due_at: datetime) -> Reminder:
        now = time.time()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO reminders (message, due_at, created_at, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (message.strip(), due_at.timestamp(), now),
            )
            rid = int(cur.lastrowid)
        return self.get(rid)  # type: ignore[return-value]

    def get(self, reminder_id: int) -> Reminder | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
            ).fetchone()
        return _row_to_reminder(row) if row else None

    def list_pending(self) -> list[Reminder]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reminders
                WHERE status = 'pending'
                ORDER BY due_at ASC
                """
            ).fetchall()
        return [_row_to_reminder(r) for r in rows]

    def due_now(self, now: float | None = None) -> list[Reminder]:
        now = now if now is not None else time.time()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reminders
                WHERE status = 'pending' AND due_at <= ?
                ORDER BY due_at ASC
                """,
                (now,),
            ).fetchall()
        return [_row_to_reminder(r) for r in rows]

    def mark_fired(self, reminder_id: int) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE reminders SET status = 'fired', fired_at = ?
                WHERE id = ?
                """,
                (now, reminder_id),
            )

    def cancel(self, reminder_id: int) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE reminders SET status = 'cancelled'
                WHERE id = ? AND status = 'pending'
                """,
                (reminder_id,),
            )
            return cur.rowcount > 0

    def cancel_matching(self, query: str) -> list[Reminder]:
        """Cancel pending reminders whose message contains query (case-insensitive)."""
        q = query.strip().lower()
        if not q:
            return []
        cancelled: list[Reminder] = []
        for rem in self.list_pending():
            if q in rem.message.lower():
                if self.cancel(rem.id):
                    cancelled.append(rem)
        return cancelled


def _row_to_reminder(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=int(row["id"]),
        message=str(row["message"]),
        due_at=float(row["due_at"]),
        created_at=float(row["created_at"]),
        status=str(row["status"]),
    )
