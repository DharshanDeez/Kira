@echo off
REM Global Kira launcher — add D:\cofounder\bin to PATH once: kira install-path
set "KIRA_ROOT=%~dp0.."
for %%I in ("%KIRA_ROOT%") do set "KIRA_ROOT=%%~fI"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
"%KIRA_ROOT%\.venv\Scripts\python.exe" -u -m kira %*
