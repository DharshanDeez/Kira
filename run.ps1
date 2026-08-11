# Kira launcher — everything on D:\cofounder
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:KIRA_ROOT = $Root
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
& "$Root\.venv\Scripts\python.exe" -m kira @args