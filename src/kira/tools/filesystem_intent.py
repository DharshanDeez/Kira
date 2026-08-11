"""Voice commands for filesystem tools + delete confirmation."""

from __future__ import annotations

import re
from pathlib import Path

from kira.tools.filesystem import FileSandbox, LOCATION_ALIASES

_LOC = r"(?:on|in)\s+(?:my\s+)?(desktop|documents|downloads|my desktop|my documents|my downloads)"

_YES = re.compile(r"^(yes|yeah|yep|confirm|do it|go ahead|sure|ok|okay)\b", re.I)
_NO = re.compile(r"^(no|nope|cancel|stop|don't|do not)\b", re.I)

_LIST = re.compile(
    rf"(?:list|show|what(?:'s| is) (?:in|on))\s+(?:files?(?:\s+(?:on|in))?\s+)?(?:my\s+)?"
    rf"(desktop|documents|downloads|my desktop|my documents|my downloads)\b",
    re.I,
)

_LIST_NAMED = re.compile(
    rf"(?:list|show)\s+(?:files?(?:\s+in)?\s+)?(.+?)\s+{_LOC}\s*$",
    re.I,
)

_SEARCH = re.compile(
    rf"(?:find|search(?:\s+for)?)\s+(?:files?(?:\s+(?:named|called))?\s+)?(.+?)"
    rf"(?:\s+{_LOC})?\s*$",
    re.I,
)

_OPEN = re.compile(rf"^open\s+(.+?)(?:\s+{_LOC})?\s*$", re.I)

_CREATE_FOLDER = re.compile(
    rf"create\s+(?:a\s+)?folder\s+(?:called\s+|named\s+)?(.+?)\s+{_LOC}\s*$",
    re.I,
)

_CREATE_FILE = re.compile(
    rf"create\s+(?:a\s+)?file\s+(?:called\s+|named\s+)?(.+?)\s+{_LOC}\s*$",
    re.I,
)

_ADD_FILE_TO_FOLDER = re.compile(
    rf"(?:add|create)\s+(?:a\s+)?file\s+(?:called\s+|named\s+)?(.+?)\s+(?:to|in)\s+"
    rf"(?:folder\s+)?(.+?)\s+{_LOC}\s*$",
    re.I,
)

_RENAME = re.compile(rf"rename\s+(.+?)\s+to\s+(.+?)(?:\s+{_LOC})?\s*$", re.I)

_DELETE = re.compile(rf"delete\s+(.+?)(?:\s+{_LOC})?\s*$", re.I)

_LOOKS_LIKE_FS = re.compile(
    r"\b(list|show|find|search|open|create|add|delete|rename|move)\b",
    re.I,
)
_FS_NOUN = re.compile(
    r"\b(desktop|documents|downloads|folder|file|directory)\b",
    re.I,
)


def looks_like_filesystem_attempt(text: str) -> bool:
    """True when user probably wanted a real file action, not chat."""
    t = text.strip()
    if not t:
        return False
    if _LOOKS_LIKE_FS.search(t) and _FS_NOUN.search(t):
        return True
    if re.search(rf"create\s+(?:a\s+)?folder\b", t, re.I):
        return True
    if re.search(rf"(?:add|create)\s+(?:a\s+)?file\b", t, re.I):
        return True
    return False


class FileCommandHandler:
    def __init__(self, sandbox: FileSandbox) -> None:
        self.sandbox = sandbox
        self._pending_delete: Path | None = None

    def has_pending(self) -> bool:
        return self._pending_delete is not None

    def clear_pending(self) -> None:
        self._pending_delete = None

    def try_handle(self, text: str) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, ""

        if self._pending_delete:
            return True, self._confirm_delete(text)

        for handler in (
            self._try_list,
            self._try_list_named,
            self._try_search,
            self._try_open,
            self._try_create_folder,
            self._try_create_file,
            self._try_add_file_to_folder,
            self._try_rename,
            self._try_delete,
        ):
            reply = handler(text)
            if reply is not None:
                return True, reply

        return False, ""

    def _confirm_delete(self, text: str) -> str:
        path = self._pending_delete
        assert path is not None
        name = path.name

        if _YES.search(text):
            self._pending_delete = None
            try:
                self.sandbox.delete(path)
                return f"Deleted {name}."
            except Exception as exc:
                return f"I couldn't delete {name}: {exc}"

        if _NO.search(text):
            self._pending_delete = None
            return "Delete cancelled."

        return f"Say yes to delete {name}, or no to cancel."

    def _format_listing(self, folder: Path, names: list[str]) -> str:
        label = folder.name
        if not names:
            return f"{label} is empty."
        spoken = ", ".join(names[:8])
        extra = f", and {len(names) - 8} more" if len(names) > 8 else ""
        return f"In {label}: {spoken}{extra}."

    def _try_list(self, text: str) -> str | None:
        match = _LIST.search(text)
        if not match:
            return None
        loc = match.group(1)
        try:
            folder, names = self.sandbox.list_dir(loc)
        except Exception as exc:
            return str(exc)
        label = self.sandbox.location_label(folder)
        if not names:
            return f"Your {label} folder is empty."
        spoken = ", ".join(names[:8])
        extra = f", and {len(names) - 8} more" if len(names) > 8 else ""
        return f"On {label}: {spoken}{extra}."

    def _try_list_named(self, text: str) -> str | None:
        match = _LIST_NAMED.search(text)
        if not match:
            return None
        folder_name, loc = match.group(1).strip(), match.group(2)
        try:
            folder, names = self.sandbox.list_named_folder(folder_name, loc)
        except FileNotFoundError:
            return f"I couldn't find folder {folder_name} on {loc}."
        except Exception as exc:
            return str(exc)
        return self._format_listing(folder, names)

    def _try_search(self, text: str) -> str | None:
        match = _SEARCH.search(text)
        if not match:
            return None
        query = match.group(1).strip()
        loc = match.group(2)
        try:
            hits = self.sandbox.search(query, loc)
        except Exception as exc:
            return str(exc)
        if not hits:
            return f"I couldn't find anything named {query}."
        if len(hits) == 1:
            return f"Found {hits[0].name}."
        names = ", ".join(h.name for h in hits[:5])
        return f"Found {len(hits)} matches: {names}."

    def _try_open(self, text: str) -> str | None:
        match = _OPEN.search(text)
        if not match:
            return None
        name = match.group(1).strip()
        loc = match.group(2)
        try:
            path = self.sandbox.find_one(name, loc)
            if path is None:
                return f"I couldn't find {name}."
            self.sandbox.open_path(path)
            return f"Opening {path.name}."
        except Exception as exc:
            return f"I couldn't open that: {exc}"

    def _try_create_folder(self, text: str) -> str | None:
        match = _CREATE_FOLDER.search(text)
        if not match:
            return None
        name, loc = match.group(1).strip(), match.group(2)
        try:
            path = self.sandbox.create_folder(name, loc)
            label = LOCATION_ALIASES.get(loc.lower(), loc)
            print(f"  [Created folder: {path}]")
            return f"Created folder {path.name} on {label}. You can see it on your Desktop now."
        except FileExistsError:
            return f"A folder called {name} already exists there."
        except Exception as exc:
            return f"I couldn't create that folder: {exc}"

    def _try_create_file(self, text: str) -> str | None:
        match = _CREATE_FILE.search(text)
        if not match:
            return None
        name, loc = match.group(1).strip(), match.group(2)
        try:
            path = self.sandbox.create_file(name, loc)
            label = LOCATION_ALIASES.get(loc.lower(), loc)
            print(f"  [Created file: {path}]")
            return f"Created file {path.name} on {label}."
        except FileExistsError:
            return f"A file called {name} already exists there."
        except Exception as exc:
            return f"I couldn't create that file: {exc}"

    def _try_add_file_to_folder(self, text: str) -> str | None:
        match = _ADD_FILE_TO_FOLDER.search(text)
        if not match:
            return None
        file_name = match.group(1).strip()
        folder_name = match.group(2).strip()
        loc = match.group(3)
        try:
            path = self.sandbox.create_file_in_folder(file_name, folder_name, loc)
            print(f"  [Created file: {path}]")
            return f"Created {path.name} inside {folder_name}."
        except FileNotFoundError:
            return f"Folder {folder_name} not found on {loc}. Create it first."
        except FileExistsError:
            return f"{file_name} already exists in {folder_name}."
        except Exception as exc:
            return f"I couldn't create that file: {exc}"

    def _try_rename(self, text: str) -> str | None:
        match = _RENAME.search(text)
        if not match:
            return None
        old, new, loc = match.group(1).strip(), match.group(2).strip(), match.group(3)
        try:
            path = self.sandbox.rename(old, new, loc)
            return f"Renamed to {path.name}."
        except Exception as exc:
            return f"I couldn't rename that: {exc}"

    def _try_delete(self, text: str) -> str | None:
        match = _DELETE.search(text)
        if not match:
            return None
        name = match.group(1).strip()
        loc = match.group(2)
        try:
            path = self.sandbox.find_one(name, loc)
            if path is None:
                return f"I couldn't find {name} to delete."
            self._pending_delete = path
            return f"Are you sure you want to delete {path.name}? Say yes to confirm."
        except Exception as exc:
            return f"I couldn't delete that: {exc}"
