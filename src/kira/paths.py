"""All Kira paths live under the project root on D: drive."""

from __future__ import annotations

import os
from pathlib import Path

# D:\cofounder — detected from package location (src/kira/paths.py → parents[2])
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_ROOT = os.environ.get("KIRA_ROOT")
if ENV_ROOT:
    PROJECT_ROOT = Path(ENV_ROOT).resolve()


def resolve_path(value: str | None, default: Path) -> Path:
    if value:
        p = Path(value)
        if not p.is_absolute():
            return (PROJECT_ROOT / p).resolve()
        return p.resolve()
    return default.resolve()


def get_paths(config: dict | None = None) -> dict[str, Path]:
    cfg = (config or {}).get("paths", {})
    root = resolve_path(cfg.get("root") or None, PROJECT_ROOT)
    data = resolve_path(cfg.get("data") or None, root / ".kira")
    models = resolve_path(cfg.get("models") or None, root / "models")
    return {"root": root, "data": data, "models": models}


def ensure_dirs(paths: dict[str, Path]) -> None:
    paths["data"].mkdir(parents=True, exist_ok=True)
    (paths["data"] / "logs").mkdir(parents=True, exist_ok=True)
    (paths["models"] / "whisper").mkdir(parents=True, exist_ok=True)
    (paths["models"] / "piper").mkdir(parents=True, exist_ok=True)
