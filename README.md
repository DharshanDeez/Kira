# Kira

Personal voice AI assistant for Windows — local, open-source, and private.

Say **"Hey Kira"** and she responds by voice. Set reminders, browse and manage files, and (in later phases) control MS Office, calendar, and more.

## Status

**Milestone 1 in progress** — push-to-talk voice loop (STT + TTS).

| Doc | Purpose |
|-----|---------|
| [docs/DISCOVERY.md](docs/DISCOVERY.md) | Product requirements |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/MVP_SCOPE.md](docs/MVP_SCOPE.md) | Phase 1 scope |

## Everything on D: drive

All project files, venv, models, and data live under `D:\cofounder\`:

```
D:\cofounder\
├── .venv\              # Python virtualenv
├── .kira\              # Kira data (logs, reminders later)
├── models\             # Piper + Whisper models
│   ├── piper\
│   └── whisper\
├── config.yaml         # Your settings (created from example)
└── src\kira\           # Source code
```

## Quick start

```powershell
cd D:\cofounder

# 1. Create venv + install (first time only)
python -m venv .venv
.venv\Scripts\pip install -e .

# 2. Download voice models (~70 MB Piper + voice)
$env:KIRA_ROOT = "D:\cofounder"
.venv\Scripts\python.exe -m kira setup

# 3. Test text-to-speech (you should hear Kira speak)
.venv\Scripts\python.exe -m kira test-tts

# 4a. Demo mode — record 5 seconds, echo back (no admin needed)
.venv\Scripts\python.exe -m kira demo

# 4b. Push-to-talk — hold Ctrl+Shift+K to speak (may need Run as Admin)
.venv\Scripts\python.exe -m kira ptt
```

Or use the launcher:

```powershell
.\run.ps1 test-tts
.\run.ps1 demo
.\run.ps1 ptt
```

## Prerequisites

- Windows 10/11
- Python 3.11+
- Microphone + speakers
- [Ollama](https://ollama.com/) (already installed — `qwen2.5:7b` used in phase 5)

## Milestone roadmap

1. **Voice skeleton** — done (STT + TTS + push-to-talk)
2. **Wake word** — done (`.\run.ps1 listen` — say "Hey Kira")
3. Reminders
4. Filesystem tools
5. Ollama agent + tray UI

## Global command (recommended)

Add `kira` to your PATH once, then run from **any** Command Prompt:

```powershell
cd D:\cofounder
.\run.ps1 install-path
```

Open a **new** CMD window:

```cmd
kira listen
```

Say **"Hey Kira"** to talk. Press **Ctrl+C** to quit.

| Command | Description |
|---------|-------------|
| `kira listen` | Wake word + **type commands** in the same window |
| `kira chat` | Type-only mode (Kira still speaks replies) |
| `kira chat --text` | Type-only, text replies only (no voice) |
| `kira stop` | Stop any background listen processes |
| `kira setup` | Download voice models |
| `kira test-tts` | Test speech output |
| `kira test-llm` | Test Ollama + voice reply |
| `kira list-mics` | List microphone devices |
| `kira mic-test` | Live mic level test |
| `kira install-path` | Add `kira` to PATH |
| `kira remove-path` | Remove `kira` from PATH |

### File commands (say after "Hey Kira")

| Say | Action |
|-----|--------|
| *List files on my Desktop* | Lists folder contents |
| *Find budget on Desktop* | Search by filename |
| *Open budget.xlsx* | Opens with default app |
| *Create folder Projects in Documents* | New folder |
| *Rename old.txt to new.txt on Desktop* | Rename |
| *Delete old.txt on Desktop* | Asks *yes* to confirm, then deletes |

Allowed folders: **Desktop**, **Documents**, **Downloads** (see `config.yaml`).

Or from the project folder without PATH:

```powershell
.\run.ps1 listen
.\run.ps1 stop
```

## Auto-start on Windows login (optional)

Kira runs in the background when you log in — silent until you say **"Hey Kira"**.

```powershell
# One-time setup (run PowerShell as yourself)
.\run.ps1 install-autostart

# Also set Ollama to start with Windows (Ollama app → Settings → Start at login)

# Remove autostart later
.\run.ps1 remove-autostart
```

**Daily flow:**
1. Turn on PC → Kira starts quietly in background
2. **"Hey Kira, …"** → conversation (Ollama replies)
3. Keep talking (25s window) or **"Goodbye Kira"** → Kira goes silent until next **"Hey Kira"**

Logs: `D:\cofounder\.kira\logs\autostart.log`

## Commands (reference)

Same as `kira <command>` after `install-path`, or `.\run.ps1 <command>` from the project folder.

| Command | Description |
|---------|-------------|
| `kira listen` | **Say "Hey Kira"** — wake word + Ollama replies |
| `kira stop` | Stop background listen processes |
| `kira setup` | Download Piper + Whisper models |
| `kira test-llm` | Test Ollama (qwen) + voice |
| `kira test-tts` | Speak a test phrase |
| `kira demo` | Record N seconds and echo |
| `kira ptt` | Push-to-talk daemon |
| `kira list-mics` | List microphone devices |
| `kira mic-test` | Live mic level test |

## License

TBD (likely MIT or Apache 2.0)
