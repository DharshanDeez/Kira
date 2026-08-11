"""Parse natural-language reminder times."""

from __future__ import annotations

import re
from datetime import datetime, timedelta


_UNIT_SECONDS = {
    "second": 1,
    "seconds": 1,
    "sec": 1,
    "secs": 1,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "mins": 60,
    "hour": 3600,
    "hours": 3600,
    "hr": 3600,
    "hrs": 3600,
}

_IN_PATTERN = re.compile(
    r"\bin\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\b",
    re.I,
)

_AT_PATTERN = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\b",
    re.I,
)


def parse_due_time(text: str, now: datetime | None = None) -> datetime | None:
    """Return due datetime from phrases like 'in 10 minutes' or 'at 3pm'."""
    now = now or datetime.now()
    lower = text.lower()

    match = _IN_PATTERN.search(lower)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower().rstrip(".")
        seconds = amount * _UNIT_SECONDS.get(unit, 60)
        return now + timedelta(seconds=seconds)

    match = _AT_PATTERN.search(lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = (match.group(3) or "").lower().replace(".", "")

        if meridiem in ("pm", "p m") and hour < 12:
            hour += 12
        elif meridiem in ("am", "a m") and hour == 12:
            hour = 0
        elif meridiem == "" and hour <= 7:
            # "at 3" without am/pm — assume PM for 1-7, else 24h style
            hour += 12 if 1 <= hour <= 7 else 0

        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due <= now:
            due += timedelta(days=1)
        return due

    return None


def format_due(due: datetime, now: datetime | None = None) -> str:
    """Human-readable due time for spoken confirmation."""
    now = now or datetime.now()
    delta = due - now
    if delta.total_seconds() < 90:
        secs = max(1, int(delta.total_seconds()))
        return f"in {secs} seconds"
    if delta.total_seconds() < 3600:
        mins = max(1, round(delta.total_seconds() / 60))
        unit = "minute" if mins == 1 else "minutes"
        return f"in {mins} {unit}"
    if due.date() == now.date():
        h = due.hour % 12 or 12
        m = due.minute
        ampm = "AM" if due.hour < 12 else "PM"
        if m:
            return f"at {h}:{m:02d} {ampm}"
        return f"at {h} {ampm}"
    return due.strftime("%A at %I:%M %p").lstrip("0")
