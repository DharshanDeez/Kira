"""Clear runtime cache files under .kira/."""

from __future__ import annotations

from pathlib import Path


def cleanup_runtime(data_dir: Path) -> None:
    for name in ("status.json", "mic_level.txt", "kira_listen.pid", "gui.lock"):
        try:
            (data_dir / name).unlink(missing_ok=True)
        except OSError:
            pass
