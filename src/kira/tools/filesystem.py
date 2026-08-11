"""Sandboxed filesystem access for voice commands."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

LOCATION_ALIASES: dict[str, str] = {
    "desktop": "Desktop",
    "my desktop": "Desktop",
    "documents": "Documents",
    "my documents": "Documents",
    "downloads": "Downloads",
    "my downloads": "Downloads",
}


class FileSandbox:
    """Only paths under configured allowed_roots."""

    def __init__(self, allowed_roots: list[str]) -> None:
        self.roots: list[Path] = []
        for raw in allowed_roots:
            p = Path(os.path.expanduser(raw)).resolve()
            p.mkdir(parents=True, exist_ok=True)
            self.roots.append(p)

    def location_path(self, hint: str | None) -> Path | None:
        if not hint:
            return self.roots[0] if self.roots else None
        key = hint.strip().lower()
        folder_name = LOCATION_ALIASES.get(key, hint.strip())
        for root in self.roots:
            if root.name.lower() == folder_name.lower():
                return root
        # Fallback: expanduser for default config (~/Desktop etc.)
        expanded = Path(os.path.expanduser(f"~/{folder_name}")).resolve()
        if expanded.is_dir() and self.is_allowed(expanded):
            return expanded
        return None

    def is_allowed(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        for root in self.roots:
            if resolved == root:
                return True
            try:
                resolved.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def resolve_in(self, parent: Path, name: str) -> Path:
        parent = parent.resolve()
        target = (parent / name.strip()).resolve()
        if not self.is_allowed(target):
            raise PermissionError(f"Not allowed: {target}")
        return target

    def list_dir(self, location: str | None = None) -> tuple[Path, list[str]]:
        folder = self.location_path(location) if location else self.roots[0]
        if folder is None or not folder.is_dir():
            raise FileNotFoundError(f"Unknown folder: {location}")
        if not self.is_allowed(folder):
            raise PermissionError(f"Not allowed: {folder}")

        entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        names = [f"{e.name}/" if e.is_dir() else e.name for e in entries[:20]]
        return folder, names

    def list_named_folder(
        self, folder_name: str, location: str
    ) -> tuple[Path, list[str]]:
        folder = self.find_one(folder_name, location)
        if folder is None:
            raise FileNotFoundError(folder_name)
        if not folder.is_dir():
            raise NotADirectoryError(folder_name)
        if not self.is_allowed(folder):
            raise PermissionError(str(folder))
        entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        names = [f"{e.name}/" if e.is_dir() else e.name for e in entries[:20]]
        return folder, names

    def create_file_in_folder(
        self, file_name: str, folder_name: str, location: str
    ) -> Path:
        folder = self.find_one(folder_name, location)
        if folder is None or not folder.is_dir():
            raise FileNotFoundError(folder_name)
        target = self.resolve_in(folder, file_name)
        target.touch(exist_ok=False)
        return target

    def search(self, query: str, location: str | None = None) -> list[Path]:
        q = query.strip().lower()
        if not q:
            return []
        roots = [self.location_path(location)] if location else self.roots
        roots = [r for r in roots if r is not None and r.is_dir()]
        matches: list[Path] = []
        for root in roots:
            for dirpath, dirnames, filenames in os.walk(root):
                base = Path(dirpath)
                if not self.is_allowed(base):
                    dirnames.clear()
                    continue
                for name in dirnames + filenames:
                    if q in name.lower():
                        matches.append(base / name)
                        if len(matches) >= 10:
                            return matches
        return matches

    def find_one(self, name: str, location: str | None = None) -> Path | None:
        target = name.strip()
        if location:
            folder = self.location_path(location)
            if folder:
                direct = folder / target
                if direct.exists():
                    return direct.resolve()
        hits = self.search(target, location)
        if not hits:
            return None
        exact = [h for h in hits if h.name.lower() == target.lower()]
        return (exact[0] if exact else hits[0]).resolve()

    def open_path(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(str(path))
        if not self.is_allowed(path):
            raise PermissionError(str(path))
        os.startfile(path)  # noqa: S606 — Windows default app

    def create_folder(self, name: str, location: str) -> Path:
        folder = self.location_path(location)
        if folder is None:
            raise FileNotFoundError(f"Unknown location: {location}")
        target = self.resolve_in(folder, name)
        target.mkdir(parents=True, exist_ok=False)
        return target

    def create_file(self, name: str, location: str) -> Path:
        folder = self.location_path(location)
        if folder is None:
            raise FileNotFoundError(f"Unknown location: {location}")
        target = self.resolve_in(folder, name)
        target.touch(exist_ok=False)
        return target

    def rename(self, old_name: str, new_name: str, location: str | None) -> Path:
        src = self.find_one(old_name, location)
        if src is None:
            raise FileNotFoundError(old_name)
        dst = self.resolve_in(src.parent, new_name)
        src.rename(dst)
        return dst

    def delete(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(str(path))
        if not self.is_allowed(path):
            raise PermissionError(str(path))
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def location_label(self, path: Path) -> str:
        name = path.name
        for hint, folder in LOCATION_ALIASES.items():
            if folder.lower() == name.lower():
                return folder
        return name
