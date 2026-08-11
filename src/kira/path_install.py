"""Add or remove Kira from the user PATH (global `kira` command in CMD)."""

from __future__ import annotations

import os
import subprocess
import winreg
from pathlib import Path

from kira.paths import PROJECT_ROOT

_BIN_DIR = PROJECT_ROOT / "bin"
_REG_PATH = r"Environment"
_REG_KEY = "Path"


def _user_path() -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH) as key:
        value, _ = winreg.QueryValueEx(key, _REG_KEY)
    return value or ""


def _set_user_path(path_value: str) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, _REG_KEY, 0, winreg.REG_EXPAND_SZ, path_value)


def _path_entries() -> list[str]:
    raw = _user_path()
    return [p.strip() for p in raw.split(";") if p.strip()]


def install_path() -> None:
    bin_dir = str(_BIN_DIR.resolve())
    entries = _path_entries()
    if bin_dir.lower() in (e.lower() for e in entries):
        print(f"PATH already contains: {bin_dir}")
    else:
        entries.append(bin_dir)
        _set_user_path(";".join(entries))
        print(f"Added to user PATH: {bin_dir}")

    _broadcast_env()
    print("\nOpen a NEW Command Prompt or PowerShell window, then run:")
    print("  kira listen")
    print("\nOther commands: kira setup | test-tts | test-llm | list-mics | mic-test | stop")


def remove_path() -> None:
    bin_dir = str(_BIN_DIR.resolve())
    entries = [e for e in _path_entries() if e.lower() != bin_dir.lower()]
    _set_user_path(";".join(entries))
    _broadcast_env()
    print(f"Removed from PATH: {bin_dir}")


def _broadcast_env() -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User'), 'User')"],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
