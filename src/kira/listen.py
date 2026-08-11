"""Milestone 2: 'Hey Kira' wake word -> listen -> respond -> follow-up chat."""

from __future__ import annotations

import enum
import queue
import re
import sys
import threading
import time

from kira.session import VoiceSession
from kira.tools.scheduler import ReminderScheduler
from kira.voice.audio import ContinuousMic, normalize_audio, stop_speech
from kira.voice.chime import play_wake_chime
from kira.voice.stt import clean_transcript
from kira.voice.wake_word import create_wake_detector, peak_block_rms, _rms

_GOODBYE = re.compile(
    r"(goodbye\s*kira|bye\s*kira|goodbye|good\s+bye|stop\s+listening|that'?s\s+all"
    r"|thanks\s+kira|thank\s+you\s+kira|bye\b)",
    re.I,
)


class State(enum.Enum):
    DORMANT = "dormant"
    RECORDING = "recording"
    FOLLOW_UP = "follow_up"


class KiraListener:
    """Wake word + multi-turn conversation; goodbye returns to silent dormant mode."""

    def __init__(self, quiet: bool = False) -> None:
        self.quiet = quiet
        self.session = VoiceSession()
        self.cfg = self.session.cfg
        assistant = self.cfg.get("assistant", {})
        wake_cfg = self.cfg.get("wake_word", {})
        self.speak_on_goodbye = bool(assistant.get("speak_on_goodbye", False))
        self.sample_rate = self.session.sample_rate
        self.device = self.session.input_device
        self.wake_window_s = float(wake_cfg.get("wake_window_seconds", 2.5))
        self.wake_check_interval = float(wake_cfg.get("check_interval_seconds", 0.6))
        self.command_max_s = float(wake_cfg.get("command_max_seconds", 8.0))
        self.silence_end_s = float(wake_cfg.get("silence_end_seconds", 1.8))
        self.silence_threshold = float(wake_cfg.get("silence_rms", 0.005))
        self.speech_threshold = float(wake_cfg.get("speech_rms", 0.008))
        self.wake_tail_s = float(wake_cfg.get("wake_tail_seconds", 1.2))
        self.follow_up_s = float(
            assistant.get("follow_up_seconds")
            or wake_cfg.get("follow_up_seconds", 25.0)
        )
        self._speaking = False
        self._speak_lock = threading.Lock()
        self._typed_queue: queue.Queue[str] = queue.Queue()
        self._stop_stdin = threading.Event()

        models_dir = self.session.paths["models"]
        print("Loading wake word detector...")
        self.wake_detector = create_wake_detector(self.cfg, models_dir)
        print("Loading command recognition model...")
        _ = self.session.stt
        _ = self.session.brain

        reminder_cfg = self.cfg.get("reminders", {})
        interval = float(reminder_cfg.get("check_interval_seconds", 2.0))
        self._scheduler = ReminderScheduler(
            self.session.reminders,
            on_fire=self._on_reminder_due,
            interval_seconds=interval,
        )

    def _speak(self, text: str) -> None:
        with self._speak_lock:
            self._speaking = True
            try:
                self.session.tts.speak(text)
            finally:
                self._speaking = False

    def _on_reminder_due(self, message: str, reminder_id: int) -> None:
        print(f"\n[Reminder #{reminder_id}] {message}")
        stop_speech()
        self._speak(f"Reminder: {message}")

    def _is_goodbye(self, text: str) -> bool:
        return bool(text and _GOODBYE.search(text.strip()))

    def _end_conversation(self) -> None:
        stop_speech()
        self._speaking = False
        if self.session._brain is not None:
            self.session.brain.clear_history()
        self.session.files.clear_pending()
        if self.speak_on_goodbye:
            self._speak("Goodbye.")
        print("\n[Kira dormant — say 'Hey Kira' to talk again]\n")

    def _start_recording(self, mic: ContinuousMic, prefix_tail: bool) -> tuple[float, bool]:
        if prefix_tail:
            tail = mic.get_recent(self.wake_tail_s)
            mic.begin_command(prefix=tail)
            speech_seen = _rms(tail) >= self.speech_threshold
        else:
            mic.begin_command()
            speech_seen = False
        return time.monotonic(), speech_seen

    def _finish_recording(self, speech_seen: bool) -> str:
        mic = self._mic
        command_audio = normalize_audio(mic.end_command())
        actual_dur = len(command_audio) / self.sample_rate
        print(f"Captured {actual_dur:.1f}s. Transcribing...")
        text = self.session.stt.transcribe(command_audio, self.sample_rate)
        text = clean_transcript(text)

        if not text:
            if speech_seen:
                self._speak("Sorry, I didn't catch that.")
            else:
                self._speak("I'm listening.")
            return "follow_up"

        return self._process_user_message(text, typed=False)

    def _process_user_message(self, text: str, *, typed: bool = False) -> str:
        """Handle voice or typed user text. Returns 'dormant' or 'follow_up'."""
        label = "You (typed)" if typed else "You"
        print(f"\n{label}: {text!r}")

        if self._is_goodbye(text):
            self._end_conversation()
            return "dormant"

        self._speak_via_session(text)
        return "follow_up"

    def _stdin_reader(self) -> None:
        while not self._stop_stdin.is_set():
            try:
                line = sys.stdin.readline()
            except Exception:
                break
            if not line:
                break
            text = line.strip()
            if text:
                self._typed_queue.put(text)

    def _drain_typed_input(self) -> str | None:
        """Process one typed line if available. Returns 'dormant', 'follow_up', or None."""
        try:
            text = self._typed_queue.get_nowait()
        except queue.Empty:
            return None
        return self._process_user_message(text, typed=True)

    def _speak_via_session(self, text: str) -> None:
        with self._speak_lock:
            self._speaking = True
            try:
                self.session.respond(text)
            finally:
                self._speaking = False

    def run(self) -> None:
        mic_label = self.device if self.device is not None else "default"
        print(f"\nKira voice assistant")
        print(f"  Project: {self.session.paths['root']}")
        print(f"  Mic:     {mic_label}")
        print(f"  Model:   {self.cfg.get('llm', {}).get('model', 'qwen2.5:7b')}")
        print(f"  Reminders: {self.session.reminders.db_path}")
        roots = ", ".join(
            str(p.name) for p in self.session.files.sandbox.roots
        )
        print(f"  Files:   {roots}")

        if self.quiet:
            print("  Mode:    quiet (no startup greeting)\n")
        else:
            print(
                "  Say 'Hey Kira' OR type a command + Enter (no wake word for typing).\n"
                "  Files: list/search/open/create/rename/delete (Desktop, Documents, Downloads).\n"
                "  Say 'goodbye Kira' to stop. Ctrl+C to quit.\n"
            )
            self._speak(
                f"Hello {self.session.user_name}. Say Hey Kira when you need me."
            )

        self._scheduler.start()

        self._mic = ContinuousMic(
            sample_rate=self.sample_rate,
            device=self.device,
            ring_seconds=self.wake_window_s + 1.0,
        )
        self._mic.start()
        print("[Dormant] Waiting for 'Hey Kira'... (mic active)")
        print("          Type a command + Enter anytime.\n")

        stdin_thread = threading.Thread(
            target=self._stdin_reader, name="kira-stdin", daemon=True
        )
        stdin_thread.start()

        state = State.DORMANT
        record_started = 0.0
        follow_up_until = 0.0
        last_wake_check = 0.0
        silence_since: float | None = None
        speech_seen = False

        try:
            while True:
                time.sleep(0.05)
                now = time.monotonic()

                typed_result = self._drain_typed_input()
                if typed_result:
                    if typed_result == "dormant":
                        state = State.DORMANT
                    else:
                        state = State.FOLLOW_UP
                        follow_up_until = now + self.follow_up_s
                        print(
                            f"\nConversation active — speak or type ({int(self.follow_up_s)}s). "
                            "Say 'goodbye Kira' to stop.\n"
                        )
                    continue

                if self._speaking:
                    continue

                if state == State.FOLLOW_UP:
                    if now > follow_up_until:
                        state = State.DORMANT
                        print("\n[Dormant] Waiting for 'Hey Kira'...\n")
                        continue

                    remaining = int(follow_up_until - now)
                    print(
                        f"\r  conversation — {remaining}s (speak freely)   ",
                        end="",
                        flush=True,
                    )

                    if self._mic.last_rms >= self.speech_threshold:
                        print("\n[Listening...]")
                        record_started, speech_seen = self._start_recording(
                            self._mic, prefix_tail=False
                        )
                        silence_since = None
                        state = State.RECORDING
                    continue

                if state == State.DORMANT:
                    if now - last_wake_check < self.wake_check_interval:
                        continue
                    last_wake_check = now

                    audio = self._mic.get_recent(self.wake_window_s)
                    if len(audio) < int(self.sample_rate * 0.8):
                        continue

                    mic_level = max(self._mic.last_rms, peak_block_rms(audio))
                    if mic_level < self.silence_threshold * 0.6:
                        print(f"\r  mic {mic_level:.0%}   ", end="", flush=True)
                        continue

                    print(f"\r  mic {mic_level:.0%} (checking...)   ", end="", flush=True)

                    heard = self.wake_detector.check(audio, self.sample_rate)
                    if not heard:
                        print(f"\r  mic {mic_level:.0%}   ", end="", flush=True)
                        continue

                    print(f"\n[Wake — heard: {heard!r}]")
                    play_wake_chime(self.sample_rate)
                    record_started, speech_seen = self._start_recording(
                        self._mic, prefix_tail=True
                    )
                    silence_since = None
                    state = State.RECORDING
                    continue

                if state == State.RECORDING:
                    rms = self._mic.last_rms
                    if rms >= self.speech_threshold:
                        speech_seen = True
                        silence_since = None
                    elif rms < self.silence_threshold:
                        if silence_since is None:
                            silence_since = now

                    elapsed = now - record_started
                    silent_for = (now - silence_since) if silence_since else 0.0

                    finished = elapsed >= self.command_max_s
                    if speech_seen and elapsed >= 0.5 and silent_for >= self.silence_end_s:
                        finished = True
                    if not speech_seen and elapsed >= 5.0:
                        finished = True

                    if not finished:
                        continue

                    result = self._finish_recording(speech_seen)
                    silence_since = None
                    speech_seen = False

                    if result == "dormant":
                        state = State.DORMANT
                    else:
                        state = State.FOLLOW_UP
                        follow_up_until = time.monotonic() + self.follow_up_s
                        print(
                            f"\nConversation active — speak or type ({int(self.follow_up_s)}s). "
                            "Say 'goodbye Kira' to stop.\n"
                        )

        except KeyboardInterrupt:
            stop_speech()
            print("\nKira stopped.")
        finally:
            self._stop_stdin.set()
            self._scheduler.stop()
            self._mic.stop()
