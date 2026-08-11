"""Kira CLI — all data and venv live on D:\\cofounder."""

from __future__ import annotations

import argparse
import logging
import sys


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(prog="kira", description="Kira voice assistant")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("setup", help="Download Piper models to D:\\cofounder\\models")
    sub.add_parser("ptt", help="Push-to-talk daemon (hold hotkey to speak)")
    sub.add_parser("test-tts", help="Test Piper text-to-speech")
    sub.add_parser("test-llm", help="Test Ollama natural language reply")
    sub.add_parser("list-mics", help="List microphone devices and indices")
    sub.add_parser("mic-test", help="Live mic level test (pick the right input_device)")
    listen = sub.add_parser("listen", help="Wake word — say 'Hey Kira'")
    listen.add_argument(
        "--quiet",
        action="store_true",
        help="No startup greeting (for autostart on Windows login)",
    )
    sub.add_parser("stop", help="Stop any background kira listen processes")
    sub.add_parser("reminders", help="List pending reminders")
    chat = sub.add_parser("chat", help="Type commands (optional voice replies)")
    chat.add_argument(
        "--text",
        action="store_true",
        help="Text replies only — no speech output",
    )
    sub.add_parser("install-path", help="Add `kira` to your user PATH (run from any CMD)")
    sub.add_parser("remove-path", help="Remove `kira` from your user PATH")
    sub.add_parser("install-autostart", help="Start Kira automatically when Windows logs in")
    sub.add_parser("remove-autostart", help="Remove Kira from Windows login startup")
    demo = sub.add_parser("demo", help="Record N seconds and echo (no hotkey)")
    demo.add_argument("--seconds", type=float, default=8.0)

    args = parser.parse_args()

    if args.command == "setup":
        from kira.setup import setup_models

        setup_models()
    elif args.command == "test-tts":
        from kira.ptt import test_tts_only

        test_tts_only()
    elif args.command == "test-llm":
        from kira.session import VoiceSession

        s = VoiceSession()
        q = "How are you doing today?"
        print(f"You: {q}")
        s.respond(q)
    elif args.command == "list-mics":
        from kira.voice.audio import list_input_devices

        list_input_devices()
    elif args.command == "mic-test":
        from kira.ptt import run_mic_test

        run_mic_test()
    elif args.command == "demo":
        from kira.ptt import PushToTalkSession

        PushToTalkSession().run_timed_demo(args.seconds)
    elif args.command == "ptt":
        from kira.ptt import PushToTalkSession

        PushToTalkSession().run_hotkey_loop()
    elif args.command == "listen":
        from kira.listen import KiraListener

        KiraListener(quiet=args.quiet).run()
    elif args.command == "stop":
        from kira.runtime_ctl import stop_listen

        n = stop_listen()
        if n:
            print(f"Stopped {n} Kira listen process(es).")
        else:
            print("No Kira listen process was running.")
    elif args.command == "reminders":
        from datetime import datetime

        from kira.config import load_config
        from kira.tools.reminder import ReminderStore
        from kira.tools.time_parse import format_due

        cfg = load_config()
        db = cfg.get("reminders", {}).get("database", "memory.db")
        store = ReminderStore(cfg["_paths"]["data"] / db)
        pending = store.list_pending()
        if not pending:
            print("No pending reminders.")
        else:
            now = datetime.now()
            for rem in pending:
                when = format_due(rem.due_datetime, now)
                print(f"  [{rem.id}] {rem.message} — {when}")
    elif args.command == "chat":
        from kira.chat import run_chat

        run_chat(speak=not args.text)
    elif args.command == "install-path":
        from kira.path_install import install_path

        install_path()
    elif args.command == "remove-path":
        from kira.path_install import remove_path

        remove_path()
    elif args.command == "install-autostart":
        from kira.autostart import install_autostart

        install_autostart()
    elif args.command == "remove-autostart":
        from kira.autostart import remove_autostart

        remove_autostart()
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
