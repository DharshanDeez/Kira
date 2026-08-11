"""Stop background Kira listen processes from the CLI."""

from __future__ import annotations

import subprocess

from kira.config import load_config
from kira.status import cleanup_runtime

_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def find_listen_pids() -> list[int]:
    script = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match 'kira listen' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=_CREATE_NO_WINDOW,
    )
    pids: list[int] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return sorted(set(pids))


def stop_listen() -> int:
    """Kill all kira listen processes. Returns count stopped."""
    pids = find_listen_pids()
    for pid in pids:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            creationflags=_CREATE_NO_WINDOW,
        )
    cleanup_runtime(load_config()["_paths"]["data"])
    return len(pids)
