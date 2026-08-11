# Personal AI Assistant — Product Discovery

> **Vision:** A Siri-like personal AI assistant — voice-first, conversational, proactive when needed.
> **Assistant name:** Kira
> **Wake word:** "Hey Kira"
> **Status:** Discovery draft — review & edit as needed

---

## Key decisions (summary)


| Decision             | Choice                                                                                       |
| -------------------- | -------------------------------------------------------------------------------------------- |
| **Stack philosophy** | Free & open-source first; everything runs **locally** by default                             |
| **LLM flexibility**  | Local via **Ollama**; optional cloud models via **OpenRouter** when you want more capability |
| **Platform order**   | **Windows desktop first** → Android sync later                                               |
| **Interaction**      | Wake word **"Hey Kira"** → Kira **always speaks back** (voice-first)                         |
| **v1 focus**         | File browse/CRUD, MS Office, reminders                                                       |
| **Growth model**     | **Phased complexity** — start simple, add integrations & proactive features over time        |
| **Budget**           | No hard cap; prefer $0 local stack, OpenRouter only when worth it                            |


---

## How to use this doc

Review each section below. **Strike or edit anything wrong.** Once locked, we write `ARCHITECTURE.md` and `MVP_SCOPE.md`.

---

## 1. Platform & access

Where should the assistant live?


| Question                                                               | Your answer                                                                                                          |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Primary device(s)? (phone, desktop, smart speaker, wearable, browser)  | **Desktop (Windows) first** — always-on background assistant on your PC                                              |
| Mobile OS? (iOS, Android, both)                                        | **Android** for phase 2 sync (not v1)                                                                                |
| Desktop OS? (Windows, macOS, Linux)                                    | **Windows 10/11** (primary); design so Linux/macOS ports are possible later                                          |
| Should it work on **one device** or **sync across all**?               | **Desktop first, sync later** — v1 is single-machine; v2+ syncs memory, reminders, and state to Android              |
| Do you need it **always available** (background) or **open app only**? | **Always available in background** — system tray / background service; listens for "Hey Kira" without opening an app |


---

## 2. Voice & interaction

How should talking to it feel?


| Question                                                                            | Your answer                                                                                                    |
| ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Wake word** (e.g. "Hey Cofounder") or **push-to-talk** (hold button) or **both**? | **Wake word primary** ("Hey Kira"); **push-to-talk as fallback** for noisy environments or false-trigger cases |
| Preferred wake word / assistant name?                                               | **Kira** / **"Hey Kira"**                                                                                      |
| Primary language(s)?                                                                | **English** first; Indian English accent tolerance; Hindi or Tamil support in a later phase                    |
| Accent / dialect preferences for TTS (text-to-speech)?                              | **Neutral / Indian English** — natural, clear, not overly robotic; open-source voice (e.g. Piper, Coqui)       |
| Should it **speak back** always, or sometimes show text only?                       | **Always speak back** for voice interactions; optional text log in a small UI panel for history/debug          |
| Max acceptable **response delay**? (e.g. < 2 sec for simple queries)                | **< 2 sec** for simple commands (reminders, open file); **< 8 sec** acceptable for complex Office/LLM tasks    |
| Should it handle **interruptions** (barge-in while speaking)?                       | **Yes — phase 2.** v1 can finish speaking; barge-in added once pipeline is stable                              |


---

## 3. What should it do? (use cases)

Rank or list your top priorities (1 = must-have for v1):


| Use case                              | Priority (1–5) | Notes                                                                                     |
| ------------------------------------- | -------------- | ----------------------------------------------------------------------------------------- |
| General Q&A / chat                    | **4**          | Local LLM; OpenRouter for harder questions                                                |
| Set reminders & alarms                | **1**          | Core v1 — voice create, list, dismiss; local storage                                      |
| Calendar (view, create, reschedule)   | **3**          | Phase 2 — Google/Outlook integration                                                      |
| Email (read, draft, send)             | **4**          | Phase 3                                                                                   |
| Messages (SMS, WhatsApp, etc.)        | **5**          | Phase 4 — Android sync required for most                                                  |
| Notes / journaling                    | **3**          | Phase 2 — local markdown notes                                                            |
| Web search & news briefings           | **3**          | Phase 2 — proactive morning brief                                                         |
| Smart home (lights, thermostat, etc.) | **5**          | Later                                                                                     |
| Navigation / maps                     | **5**          | Android phase                                                                             |
| Music / media control                 | **4**          | Phase 3 — local / Spotify                                                                 |
| Phone calls                           | **5**          | Later                                                                                     |
| File search on device                 | **1**          | Core v1 — browse, search, open files by voice                                             |
| Code / dev helper                     | **3**          | Phase 2 — read/edit project files                                                         |
| Fitness / health tracking             | **5**          | Later                                                                                     |
| Shopping / orders                     | **5**          | Later                                                                                     |
| Other: **MS Office CRUD**             | **1**          | Core v1 — Word/Excel/PowerPoint: open, read summary, create/edit/save documents via voice |


**Describe your ideal "day with the assistant" in 3–5 sentences:**

> I say "Hey Kira" at my desk and she responds out loud. I ask her to remind me in 30 minutes, open a spreadsheet, or create a Word doc with meeting notes. She browses my files, finds what I need, and handles basic Office tasks without me touching the keyboard. Over time she gets smarter — morning briefings, calendar, email, and eventually the same Kira on my Android phone. Everything private on my machine unless I explicitly route a hard question through OpenRouter.

---

## 4. Proactive vs reactive


| Question                                                                                              | Your answer                                                                                                       |
| ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Should it **only respond when asked**, or also **proactively notify** you?                            | **Reactive in v1** (only when you say "Hey Kira"); **proactive in phase 2+** (reminders fire, optional briefings) |
| Examples of proactive behavior you want? (morning briefing, meeting reminders, "you're running late") | Reminder alerts spoken aloud; later: morning briefing (calendar + weather + todos), meeting nudge 10 min before   |
| Quiet hours / Do Not Disturb rules?                                                                   | **Yes** — configurable quiet hours (e.g. 11pm–7am); only critical reminders break through                         |
| How aggressive should follow-ups be? (e.g. nag about unfinished tasks)                                | **Low** — remind once, optional snooze; no nagging unless you ask for persistent follow-ups                       |


---

## 5. Memory & personalization


| Question                                                                              | Your answer                                                                          |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Should it **remember facts about you** across sessions? (name, preferences, routines) | **Yes** — name (Dharshan), preferred folders, Office defaults, wake word sensitivity |
| Should it **learn from corrections**? ("Don't call me that")                          | **Yes** — store corrections in local memory file                                     |
| Memory scope: **session only**, **weeks**, **forever**?                               | **Forever** (local SQLite + optional markdown profile); user can prune               |
| Can you **delete / export** your memory data?                                         | **Yes** — export JSON/markdown; one-click wipe                                       |
| Should it know about **family members / contacts** by name?                           | **Phase 2** — local contacts file you curate                                         |
| Personality tone? (formal, friendly, witty, minimal)                                  | **Friendly, concise, capable** — JARVIS-adjacent: helpful co-pilot, not chatty       |


---

## 6. Integrations & data sources

Which services should v1 connect to?


| Service                                  | Needed for v1? (Y/N)           | Account you have                                       |
| ---------------------------------------- | ------------------------------ | ------------------------------------------------------ |
| Google Calendar                          | **Y** (phase 2)                | TBD                                                    |
| Google Gmail                             | **Y** (phase 3)                | TBD                                                    |
| Outlook / Microsoft 365                  | **N** (phase 2)                | TBD                                                    |
| Apple Calendar / iCloud                  | **N**                          | —                                                      |
| Notion                                   | **N** (phase 3+)               | TBD                                                    |
| Todoist / Tasks app                      | **N**                          | —                                                      |
| Spotify                                  | **N** (phase 3)                | TBD                                                    |
| Smart home (HomeKit, Google Home, Alexa) | **N**                          | —                                                      |
| Weather                                  | **N** (phase 2, for briefings) | —                                                      |
| Local filesystem                         | **Y**                          | Windows user profile, Documents, Desktop, custom roots |
| **MS Office (Word, Excel, PowerPoint)**  | **Y**                          | Local install — automate via COM (Windows)             |
| **Ollama (local LLM)**                   | **Y**                          | Self-hosted                                            |
| **OpenRouter (optional cloud LLM)**      | **Y** (optional)               | API key when you want stronger models                  |


---

## 7. Privacy, security & AI backend


| Question                                                                          | Your answer                                                                                                                                |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Cloud LLM** (OpenAI, Claude, Gemini) vs **local model** (Ollama) vs **hybrid**? | **Hybrid:** **Ollama local default**; **OpenRouter** for flexibility (pick model per task); cloud is opt-in per request or for "hard mode" |
| OK to send voice audio to cloud for STT (speech-to-text)?                         | **No for v1** — local **Whisper** (or faster-whisper) only; audio never leaves device                                                      |
| Sensitive data that must **never** leave your device?                             | **Voice recordings, file contents, Office docs, memory/profile** — unless you explicitly ask Kira to use OpenRouter for a query            |
| Single user or multi-user (household)?                                            | **Single user** (Dharshan); multi-user is out of scope for now                                                                             |
| Biometric / PIN lock for sensitive actions (send email, payments)?                | **Phase 3** — PIN or Windows Hello before send/delete/export                                                                               |
| Monthly budget for API costs? (rough $ range)                                     | **No hard budget** — default $0 (local); OpenRouter usage as needed with no cap                                                            |


---

## 8. Offline & reliability


| Question                                               | Your answer                                                                                             |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Must any features work **offline**? Which ones?        | **Yes — all core v1 offline:** wake word, STT, TTS, local LLM, file CRUD, Office automation, reminders  |
| Acceptable behavior when internet is down?             | **Fully functional** for local features; OpenRouter/web tools gracefully unavailable with spoken notice |
| Should conversations be **stored locally**? Encrypted? | **Yes — local SQLite logs;** encrypt at rest (phase 2); v1 plain local with user data folder            |


---

## 9. Technical preferences (optional)


| Question                                                                                 | Your answer                                                                                                                               |
| ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Preferred languages/frameworks? (Python, TypeScript, React Native, Flutter, etc.)        | **Python** backend (voice, agent, tools, Office COM); **Electron or Tauri** for optional desktop UI; **Kotlin** for future Android client |
| Build **from scratch** vs use **existing agent frameworks** (LangGraph, etc.)?           | **Framework-assisted** — LangGraph or lightweight custom agent loop; don't reinvent STT/TTS                                               |
| Open to **third-party voice APIs** (Deepgram, ElevenLabs, Whisper) vs fully open-source? | **Fully open-source for v1** — Whisper, Piper/Coqui TTS, open wake word (e.g. openWakeWord / Porcupine free tier fallback)                |
| Target timeline for **first usable prototype**?                                          | **~4–6 weeks** — "Hey Kira" → speak → reminder + open file                                                                                |
| Target timeline for **Siri-like daily driver**?                                          | **~3–4 months** — Office CRUD, stable wake word, memory, proactive reminders; Android sync after desktop is solid                         |


---

## 10. Success criteria

How will you know v1 is "good enough"?


| Question                                  | Your answer                                                                                                                                                                                      |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 3 things that **must work** in v1         | 1. **"Hey Kira" wake word** → Kira **speaks** a response 2. **Reminders** — set, list, and fire on time (spoken alert) 3. **Files** — browse, search, open, create, rename, delete on local disk |
| 3 things that can **wait for v2**         | 1. **MS Office deep CRUD** (create/edit Word/Excel by voice) 2. **Android sync** and mobile wake word 3. **Proactive briefings**, calendar, email                                                |
| One **demo scenario** you'd show a friend | *"Hey Kira, remind me in 10 minutes to call mom. Find my budget spreadsheet on Desktop and open it. What files did I edit today?"* — all voice, all local, she talks back.                       |


---

## 11. Open questions / ideas

(Add anything else — constraints, inspirations, apps you like, things Siri does badly that you want to fix)

> - **Inspiration:** JARVIS — capable, calm, voice-first.
> - **Fix what Siri gets wrong:** Actually useful on desktop, full file access, no cloud lock-in, real Office control.
> - **Phased complexity roadmap:**
>   - **Phase 1 (MVP):** Wake word + STT + TTS + Ollama + reminders + file browse/CRUD
>   - **Phase 2:** MS Office automation, memory/personalization, proactive reminder speech, notes
>   - **Phase 3:** OpenRouter routing, calendar/email, dev helper, encrypted logs
>   - **Phase 4:** Android app + sync, messaging, smart home, barge-in
> - **Open questions for Dharshan to edit:**
>   - Which **Ollama model size** can your PC run? (8B vs 70B — affects quality vs speed)
>   - **Office version** — Microsoft 365 desktop vs standalone 2021?
>   - **GPU available?** (NVIDIA CUDA speeds Whisper + LLM a lot)
>   - Hindi/regional language — which phase?

---

## Next steps (after discovery)

1. ~~Review your answers together~~ ✓
2. ~~Write `docs/ARCHITECTURE.md` — system design, stack, phases~~ ✓
3. ~~Write `docs/MVP_SCOPE.md` — exact v1 feature cut~~ ✓
4. **Implement phase 1** ← **you are here**

---

*Last updated: discovery draft filled from Dharshan’s requirements (local OSS, OpenRouter optional, desktop-first, Kira voice assistant)*