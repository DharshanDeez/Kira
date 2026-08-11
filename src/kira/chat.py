"""Interactive text chat — type commands, optional voice replies."""

from __future__ import annotations

import threading

from kira.session import VoiceSession
from kira.tools.scheduler import ReminderScheduler
from kira.voice.audio import stop_speech

_GOODBYE = ("goodbye", "goodbye kira", "bye", "quit", "exit")


def run_chat(*, speak: bool = True) -> None:
    session = VoiceSession()
    cfg = session.cfg
    reminder_cfg = cfg.get("reminders", {})
    interval = float(reminder_cfg.get("check_interval_seconds", 2.0))
    speak_lock = threading.Lock()
    speaking = {"active": False}

    def on_reminder(message: str, rid: int) -> None:
        if not speak:
            print(f"\n[Reminder #{rid}] {message}")
            return
        with speak_lock:
            speaking["active"] = True
            try:
                stop_speech()
                print(f"\n[Reminder #{rid}] {message}")
                session.tts.speak(f"Reminder: {message}")
            finally:
                speaking["active"] = False

    scheduler = ReminderScheduler(session.reminders, on_fire=on_reminder, interval_seconds=interval)
    scheduler.start()

    mode = "voice + text" if speak else "text only"
    print(f"\nKira chat ({mode})")
    print("  Type a command and press Enter.")
    print("  Reminders, files, and chat work here — no wake word needed.")
    print("  Type quit or goodbye to exit.\n")

    try:
        while True:
            try:
                line = input("You> ").strip()
            except EOFError:
                break

            if not line:
                continue
            if line.lower() in _GOODBYE:
                print("Goodbye.")
                break

            if speak and speaking["active"]:
                continue

            reply = session.respond(line, speak=speak)
            if not speak and reply:
                print(f"Kira: {reply}")

    except KeyboardInterrupt:
        print("\nGoodbye.")
    finally:
        scheduler.stop()
