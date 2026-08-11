# Starts Kira in the background when Windows logs in (no window, no greeting).
$Root = "D:\cofounder"
$env:KIRA_ROOT = $Root
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$Log = Join-Path $Root ".kira\logs\autostart.log"
New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null
$Python = Join-Path $Root ".venv\Scripts\pythonw.exe"
Start-Process -FilePath $Python `
    -ArgumentList "-m", "kira", "listen", "--quiet" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $Log `
    -RedirectStandardError $Log
