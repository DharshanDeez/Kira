"""Fast-path voice commands for reminders (no LLM wait)."""

from __future__ import annotations

import re
from datetime import datetime

from kira.tools.reminder import ReminderStore
from kira.tools.time_parse import format_due, parse_due_time

# Whisper often mishears "remind" as "find", "mind", etc.
_STT_FIXES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bfind me\b", re.I), "remind me"),
    (re.compile(r"\bmind me\b", re.I), "remind me"),
    (re.compile(r"\bremind her\b", re.I), "remind me"),
    (re.compile(r"\bremind him\b", re.I), "remind me"),
    (re.compile(r"\breminder me\b", re.I), "remind me"),
    (re.compile(r"\bremind me to to\b", re.I), "remind me to"),
]

_REMIND_VERB = r"(?:remind|find|mind|set(?:\s+a)?\s+reminder)"

_LIST_PATTERN = re.compile(
    r"(what are my reminders|list my reminders|show my reminders|"
    r"my reminders|any reminders|do i have reminders)",
    re.I,
)

_CANCEL_PATTERN = re.compile(
    r"(cancel|delete|remove|clear)\s+(?:my\s+)?reminder(?:s)?(?:\s+about|\s+to|\s+for)?\s+(.+)",
    re.I,
)

_CREATE_IN_TO = re.compile(
    rf"{_REMIND_VERB}(?:\s+me)?\s+in\s+(\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?))\s+to\s+(.+)",
    re.I,
)

_CREATE_IN_NEED = re.compile(
    rf"{_REMIND_VERB}(?:\s+me)?\s+in\s+(\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?))\s+(?:i need to|i have to|to)\s+(.+)",
    re.I,
)

_CREATE_TO_IN = re.compile(
    rf"{_REMIND_VERB}(?:\s+me)?\s+to\s+(.+?)\s+in\s+(\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?))\b",
    re.I,
)

_CREATE_AT = re.compile(
    rf"{_REMIND_VERB}(?:\s+me)?(?:\s+to)?\s+(.+?)\s+at\s+(\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm|a\.m\.|p\.m\.)?)",
    re.I,
)

_CREATE_AT_ALT = re.compile(
    rf"{_REMIND_VERB}(?:\s+me)?\s+at\s+(\d{{1,2}}(?::\d{{2}})?\s*(?:am|pm|a\.m\.|p\.m\.)?)\s+to\s+(.+)",
    re.I,
)

_ACTION_IN = re.compile(
    r"(?:to\s+)?(?:watch|see|check|take|call|do)\s+(.+?)\s+in\s+(\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?))\b",
    re.I,
)

_SET_REMINDER = re.compile(
    r"set\s+(?:a\s+)?reminder(?:\s+for)?\s+(.+)",
    re.I,
)

_LOOKS_LIKE_REMINDER = re.compile(
    rf"{_REMIND_VERB}|set\s+(?:a\s+)?reminder|\bin\s+\d+\s*(?:minutes?|mins?|hours?|hrs?)\b",
    re.I,
)


def normalize_reminder_text(text: str) -> str:
    out = text.strip()
    for pattern, replacement in _STT_FIXES:
        out = pattern.sub(replacement, out)
    return out


def looks_like_reminder_attempt(text: str) -> bool:
    """True when user probably wanted a reminder but parsing may have failed."""
    normalized = normalize_reminder_text(text)
    if not _LOOKS_LIKE_REMINDER.search(normalized):
        return False
    return parse_due_time(normalized) is not None


def try_handle_reminder(text: str, store: ReminderStore) -> tuple[bool, str]:
    """
    Handle reminder create / list / cancel without Ollama.
    Returns (handled, spoken_reply).
    """
    text = normalize_reminder_text(text.strip())
    if not text:
        return False, ""

    if _LIST_PATTERN.search(text):
        return True, _list_reminders(store)

    cancel = _CANCEL_PATTERN.search(text)
    if cancel:
        return True, _cancel_reminders(store, cancel.group(1))

    create_reply = _try_create(text, store)
    if create_reply:
        return True, create_reply

    if looks_like_reminder_attempt(text):
        return True, (
            "I couldn't save that reminder. "
            'Try saying: remind me in 5 minutes to, then what you need.'
        )

    return False, ""


def _list_reminders(store: ReminderStore) -> str:
    pending = store.list_pending()
    if not pending:
        return "You have no pending reminders."
    now = datetime.now()
    parts: list[str] = []
    for rem in pending[:5]:
        when = format_due(rem.due_datetime, now)
        parts.append(f"{rem.message}, {when}")
    if len(pending) == 1:
        return f"You have one reminder: {parts[0]}."
    extra = f" and {len(pending) - 5} more" if len(pending) > 5 else ""
    return f"You have {len(pending)} reminders{extra}: " + "; ".join(parts) + "."


def _cancel_reminders(store: ReminderStore, query: str) -> str:
    cancelled = store.cancel_matching(query)
    if not cancelled:
        return f"I couldn't find a pending reminder about {query}."
    if len(cancelled) == 1:
        return f"Cancelled your reminder to {cancelled[0].message}."
    names = ", ".join(r.message for r in cancelled)
    return f"Cancelled {len(cancelled)} reminders: {names}."


def _try_create(text: str, store: ReminderStore) -> str | None:
    now = datetime.now()

    match = _CREATE_IN_TO.search(text)
    if match:
        due = parse_due_time(f"in {match.group(1)}", now)
        message = _clean_message(match.group(2))
        if due and message:
            return _save(store, message, due, now)

    match = _CREATE_IN_NEED.search(text)
    if match:
        due = parse_due_time(f"in {match.group(1)}", now)
        message = _clean_message(match.group(2))
        if due and message:
            return _save(store, message, due, now)

    match = _CREATE_TO_IN.search(text)
    if match:
        due = parse_due_time(f"in {match.group(2)}", now)
        message = _clean_message(match.group(1))
        if due and message:
            return _save(store, message, due, now)

    match = _CREATE_AT_ALT.search(text)
    if match:
        due = parse_due_time(f"at {match.group(1)}", now)
        message = _clean_message(match.group(2))
        if due and message:
            return _save(store, message, due, now)

    match = _CREATE_AT.search(text)
    if match:
        due = parse_due_time(f"at {match.group(2)}", now)
        message = _clean_message(match.group(1))
        if due and message:
            return _save(store, message, due, now)

    match = _ACTION_IN.search(text)
    if match:
        due = parse_due_time(f"in {match.group(2)}", now)
        message = _clean_message(match.group(1))
        if due and message:
            return _save(store, message, due, now)

    match = _SET_REMINDER.search(text)
    if match:
        body = match.group(1)
        due = parse_due_time(body, now)
        if due:
            message = _extract_message(body)
            if message:
                return _save(store, message, due, now)

    if re.search(rf"{_REMIND_VERB}", text, re.I):
        due = parse_due_time(text, now)
        message = _extract_message(text)
        if due and message:
            return _save(store, message, due, now)

    return None


def _clean_message(message: str) -> str:
    message = message.strip(" .,!?:;")
    message = re.sub(r"^(?:to|about|for)\s+", "", message, flags=re.I)
    return message.strip()


def _extract_message(text: str) -> str:
    msg = text
    for pattern in (
        rf"^{_REMIND_VERB}(?:\s+me)?\s+",
        r"^set\s+(?:a\s+)?reminder(?:\s+for)?\s+",
        r"\bin\s+\d+\s*(?:seconds?|secs?|minutes?|mins?|hours?|hrs?)\b",
        r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?\b",
        r"^\s+to\s+",
        r"^(?:i need to|i have to)\s+",
    ):
        msg = re.sub(pattern, " ", msg, flags=re.I)
    return _clean_message(msg)


def _save(
    store: ReminderStore, message: str, due: datetime, now: datetime
) -> str:
    rem = store.create(message, due)
    when = format_due(due, now)
    print(
        f"  [Reminder #{rem.id} saved — fires at {due.strftime('%H:%M:%S')} — {message}]"
    )
    return f"Got it. I'll remind you {when} to {message}."
