# Kira — MVP Scope (Phase 1)

> Exact feature cut for the first shippable prototype (~4–6 weeks).
> See also: [DISCOVERY.md](./DISCOVERY.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## MVP goal

**You can say "Hey Kira", ask her to set a reminder or manage files, and she speaks back — fully offline on Windows.**

### Demo script (success = this works reliably)

```
You:  "Hey Kira"
Kira: [listening tone]
You:  "Remind me in 10 minutes to call mom"
Kira: "Got it. I'll remind you in 10 minutes to call mom."

[10 minutes later]
Kira: "Reminder: call mom"

You:  "Hey Kira, find budget on my Desktop and open it"
Kira: "Opening budget.xlsx"

You:  "Hey Kira, create a folder called Projects in Documents"
Kira: "Created Projects in Documents"
```

---

## In scope (v1)

### Voice pipeline

| Feature | Requirement |
|---------|-------------|
| Wake word | **"Hey Kira"** via openWakeWord |
| Push-to-talk | Global hotkey `Ctrl+Shift+K` as fallback |
| STT | faster-whisper, English, local only |
| TTS | Piper, always speaks responses |
| Listening feedback | Short audio cue when wake word detected |
| Barge-in | **Out of scope** — wait until phase 2 |

### Agent & LLM

| Feature | Requirement |
|---------|-------------|
| Local LLM | Ollama default model (configurable) |
| Tool calling | Agent selects reminder / filesystem tools |
| Fast path | Regex/deterministic parse for common reminder + file commands (no LLM wait) |
| OpenRouter | **Out of scope** for v1 |
| General chat | Basic Q&A via Ollama — best-effort, not optimized |

### Reminders

| Feature | Requirement |
|---------|-------------|
| Create | "Remind me in X minutes/hours to …" / "at 3pm …" |
| List | "What are my reminders?" |
| Cancel | "Cancel my reminder about …" |
| Fire | Spoken alert at due time via TTS |
| Storage | SQLite in `%USERPROFILE%\.kira\memory.db` |
| Quiet hours | **Out of scope** for v1 — fire always (add in phase 2) |
| Snooze | **Out of scope** for v1 |

### Filesystem

| Feature | Requirement |
|---------|-------------|
| Browse | "List files in Desktop / Documents / …" |
| Search | "Find files named budget" (filename match) |
| Open | Open file with default Windows app |
| Create | Create file or folder |
| Rename | Rename file or folder |
| Delete | Delete with **voice confirmation** |
| Sandbox | Only allowlisted paths in config |
| Read content | **Out of scope** — no "summarize this PDF" yet |

### Memory & personalization

| Feature | Requirement |
|---------|-------------|
| User name | Knows "Dharshan" from config |
| Conversation log | SQLite log of transcripts + responses |
| Long-term memory | **Out of scope** — phase 2 |
| Corrections learning | **Out of scope** — phase 2 |

### MS Office

| Feature | Requirement |
|---------|-------------|
| All Office CRUD | **Out of scope for v1** — phase 2 via COM |
| Open Office files | **In scope** — "open budget.xlsx" uses default app (may be Excel) |

### UI

| Feature | Requirement |
|---------|-------------|
| System tray | Icon showing idle / listening / speaking |
| Conversation log | Simple scrollable window |
| Settings | Minimal: mic device, Ollama model, allowed folders |
| Installer | Manual clone + run for v1; proper installer phase 2 |

### Platform

| Feature | Requirement |
|---------|-------------|
| OS | Windows 10/11 only |
| Background | Daemon runs on login (manual start OK for v1) |
| Offline | 100% of v1 features work without internet |
| Android | **Out of scope** |

---

## Out of scope (v1) — explicitly deferred

| Feature | Phase |
|---------|-------|
| MS Office create/edit/save by voice | 2 |
| Proactive morning briefing | 2 |
| Quiet hours / DND | 2 |
| Long-term memory & profile | 2 |
| Notes / journaling | 2 |
| OpenRouter / cloud LLM | 3 |
| Google Calendar / Gmail | 3 |
| Barge-in while speaking | 2 |
| Android sync | 4 |
| Encrypted database | 2 |
| Windows Service installer | 2 (manual start OK for v1) |
| Hindi / Tamil | 4+ |

---

## Implementation milestones

### Milestone 1 — Voice skeleton (week 1–2)

- [ ] Project scaffold (`pyproject.toml`, `src/kira/`)
- [ ] Audio capture + playback
- [ ] Piper TTS: "Hello Dharshan, Kira is ready"
- [ ] faster-whisper STT from mic
- [ ] Push-to-talk end-to-end: speak → text → echo via TTS
- [ ] Config file + `.kira` data dir

**Exit criteria:** Push-to-talk conversation loop works.

### Milestone 2 — Wake word (week 2–3)

- [ ] openWakeWord integration
- [ ] Custom or adapted "Hey Kira" model
- [ ] State machine: idle → wake → listen → process → speak
- [ ] Listening chime

**Exit criteria:** "Hey Kira" triggers listening without button.

### Milestone 3 — Reminders (week 3–4)

- [ ] SQLite schema for reminders
- [ ] `reminder` tool: create, list, cancel
- [ ] Natural language time parsing ("in 10 minutes", "at 3pm")
- [ ] Background scheduler thread
- [ ] Spoken fire at due time
- [ ] Fast path without LLM for clear reminder phrases

**Exit criteria:** Demo reminder script works.

### Milestone 4 — Filesystem (week 4–5)

- [ ] `filesystem` tool with path sandbox
- [ ] list, search, open, create, rename, delete (+ confirmation)
- [ ] Agent wiring for file intents
- [ ] Fast path for "open …" / "list files in …"

**Exit criteria:** Demo file script works.

### Milestone 5 — Polish & tray UI (week 5–6)

- [ ] Ollama integration for ambiguous commands
- [ ] System tray icon + status
- [ ] Conversation log window
- [ ] Basic settings UI
- [ ] Error handling: mic missing, Ollama down, permission denied
- [ ] README with setup instructions

**Exit criteria:** Full demo script runs reliably 5 times in a row.

---

## Acceptance tests

| # | Test | Pass condition |
|---|------|----------------|
| 1 | Wake word | "Hey Kira" activates listening within 500 ms |
| 2 | Reminder create | Reminder stored and confirmed by voice |
| 3 | Reminder fire | Alert spoken within 30 s of due time |
| 4 | File open | Correct file opens in default app |
| 5 | File create | Folder/file appears on disk |
| 6 | File delete | Requires confirmation; file removed after "yes" |
| 7 | Offline | Airplane mode — all above still work |
| 8 | Latency | Simple reminder command < 2 s wake-to-first-speech |

---

## Config defaults (v1)

```yaml
# config.example.yaml
user:
  name: Dharshan

wake_word:
  phrase: "hey kira"
  sensitivity: 0.5

voice:
  stt_model: "base"          # faster-whisper: tiny, base, small
  tts_voice: "en_GB-alan-medium"  # Piper voice — swap for Indian English pack

llm:
  provider: ollama
  model: "llama3.1:8b"
  base_url: "http://localhost:11434"

filesystem:
  allowed_roots:
    - "~/Desktop"
    - "~/Documents"
    - "~/Downloads"

hotkey:
  push_to_talk: "ctrl+shift+k"
```

---

## Risks & mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Wake word false positives | Annoying | Tune sensitivity; push-to-talk fallback |
| Whisper too slow on CPU | Misses latency target | Use `tiny`/`base`; enable CUDA |
| Ollama not running | Agent fails | Health check on startup; spoken error |
| Office expected in v1 | Scope creep | Document clearly: open only, not edit |
| COM automation fragile | Phase 2 delay | Spike early in phase 2, not v1 |

---

## After MVP — phase 2 preview

1. MS Office COM (Word/Excel/PPT voice CRUD)
2. User memory profile + corrections
3. Quiet hours for reminders
4. Proactive spoken alerts polish
5. Local markdown notes

---

*Last updated: MVP scope v1 aligned with DISCOVERY.md*
