"""Background thread — speak when reminders are due."""

from __future__ import annotations

import threading
import time
from typing import Callable

from kira.tools.reminder import ReminderStore


class ReminderScheduler:
    def __init__(
        self,
        store: ReminderStore,
        on_fire: Callable[[str, int], None],
        interval_seconds: float = 2.0,
    ) -> None:
        self.store = store
        self.on_fire = on_fire
        self.interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="kira-reminders", daemon=True)
        self._thread.start()
        pending = len(self.store.list_pending())
        if pending:
            print(f"  Reminders: {pending} pending in queue")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            for rem in self.store.due_now():
                self.on_fire(rem.message, rem.id)
                self.store.mark_fired(rem.id)
            self._stop.wait(self.interval)
