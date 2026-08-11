"""Load Kira configuration from D:\\cofounder\\config.yaml."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

from kira.paths import PROJECT_ROOT, ensure_dirs, get_paths

# Keep HuggingFace download noise down in the terminal
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
for _logger in ("httpx", "httpcore", "huggingface_hub", "faster_whisper"):
    logging.getLogger(_logger).setLevel(logging.WARNING)


def config_file() -> Path:
    return PROJECT_ROOT / "config.yaml"


def parse_input_device(value) -> int | None:
    if value is None or value == "" or str(value).lower() == "null":
        return None
    return int(value)


def load_config() -> dict[str, Any]:
    path = config_file()
    example = PROJECT_ROOT / "config.example.yaml"
    if not path.exists():
        if example.exists():
            shutil.copy(example, path)
        else:
            raise FileNotFoundError(f"Missing config: {path}")
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    paths = get_paths(cfg)
    ensure_dirs(paths)
    cfg["_paths"] = paths
    return cfg


def save_config_updates(updates: dict[str, Any]) -> None:
    """Merge updates into config.yaml (e.g. voice.input_device, llm.model)."""
    path = config_file()
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    for section, values in updates.items():
        if not isinstance(values, dict):
            cfg[section] = values
            continue
        cfg.setdefault(section, {})
        cfg[section].update(values)

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
