"""Windows autostart — run Kira when you log in."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from kira.paths import PROJECT_ROOT

TASK_NAME = "KiraVoiceAssistant"


def _startup_script() -> Path:
    return PROJECT_ROOT / "scripts" / "kira_autostart.ps1"


def install_autostart() -> None:
    script = _startup_script()
    if not script.exists():
        raise FileNotFoundError(f"Missing {script}")

    ps = f"""
$TaskName = '{TASK_NAME}'
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-WindowStyle Hidden -ExecutionPolicy Bypass -File "{script}"'
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Kira voice assistant — Hey Kira on login'
Write-Host 'Installed. Kira will start when you log in to Windows.'
"""
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
    )
    print(f"Autostart task '{TASK_NAME}' registered.")
    print("Requires: Ollama running (set Ollama to start with Windows too).")


def remove_autostart() -> None:
    ps = f"""
Unregister-ScheduledTask -TaskName '{TASK_NAME}' -Confirm:$false -ErrorAction SilentlyContinue
Write-Host 'Removed autostart task.'
"""
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=True,
    )
    print(f"Autostart task '{TASK_NAME}' removed.")
