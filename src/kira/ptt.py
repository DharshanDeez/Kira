"""Milestone 1: push-to-talk voice loop."""

from __future__ import annotations

import logging
import threading
import time

from kira.config import load_config, parse_input_device
from kira.session import VoiceSession
from kira.voice.audio import list_input_devices, monitor_mic_level

log = logging.getLogger(__name__)


class PushToTalkSession:
    def __init__(self) -> None:
        self.session = VoiceSession()
        self.cfg = self.session.cfg
        self.paths = self.session.paths
        voice = self.cfg.get("voice", {})
        self.sample_rate = self.session.sample_rate
        self.hotkey = self.session.hotkey
        self._user_name = self.session.user_name
        self.input_device = self.session.input_device
        self.tts = self.session.tts
        self.recorder = self.session.recorder
        self._recording = False
        self._lock = threading.Lock()

    @property
    def stt(self):
        return self.session.stt

    def startup_greeting(self) -> None:
        self.tts.speak(
            f"Hello {self._user_name}. Kira is ready. Hold {self.hotkey} to talk."
        )

    def _on_press(self) -> None:
        with self._lock:
            if self._recording:
                return
            self._recording = True
            log.info("Listening...")
            self.recorder.start()

    def _on_release(self) -> None:
        with self._lock:
            if not self._recording:
                return
            self._recording = False
            audio = self.recorder.stop()

        if audio.size == 0:
            self.tts.speak("I didn't hear anything.")
            return

        log.info("Transcribing...")
        text = self.stt.transcribe(audio, self.sample_rate)
        if not text:
            self.tts.speak("Sorry, I couldn't understand that.")
            return

        log.info("You said: %s", text)
        self.session.respond(text)

    def run_hotkey_loop(self) -> None:
        import keyboard

        mic_label = self.input_device if self.input_device is not None else "default"
        print(f"\nKira push-to-talk active on D: drive")
        print(f"  Project: {self.paths['root']}")
        print(f"  Mic:     {mic_label}")
        print(f"\nHold [{self.hotkey}] to speak. Ctrl+C to quit.\n")

        self.startup_greeting()

        held = False
        try:
            while True:
                pressed = keyboard.is_pressed(self.hotkey)
                if pressed and not held:
                    held = True
                    self._on_press()
                elif not pressed and held:
                    held = False
                    self._on_release()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nKira stopped.")

    def run_timed_demo(self, seconds: float = 8.0) -> None:
        mic_label = self.input_device if self.input_device is not None else "default"
        print("\n--- Kira voice demo ---")
        print(f"Mic device: {mic_label}  |  STT: {self.session._stt_kwargs['model_size']}")
        print("Loading models...")
        _ = self.stt

        monitor_mic_level(self.input_device, self.sample_rate, seconds=2.5)

        print("Get ready to speak...")
        for i in range(3, 0, -1):
            print(f"  {i}...")
            time.sleep(1)

        print(f"\n>>> RECORDING {seconds:.0f}s — SPEAK NOW <<<\n")
        audio = self.recorder.record_for_seconds(seconds)
        duration = len(audio) / self.sample_rate if audio.size else 0
        print(f"Captured {duration:.1f}s of audio. Transcribing...")

        text = self.stt.transcribe(audio, self.sample_rate)
        print(f"Heard: {text!r}")

        if text:
            print("Kira speaking...")
            self.session.respond(text)
            print("Done.")
        else:
            print("No speech detected. Try: .\\run.ps1 list-mics")
            self.tts.speak("I couldn't understand that.")


def test_tts_only() -> None:
    PushToTalkSession().tts.speak(
        f"Hello {load_config().get('user', {}).get('name', 'there')}. "
        "Kira text to speech is working."
    )


def run_mic_test() -> None:
    cfg = load_config()
    voice = cfg.get("voice", {})
    device = parse_input_device(voice.get("input_device"))
    rate = int(voice.get("sample_rate", 16000))
    list_input_devices()
    monitor_mic_level(device, rate, seconds=5.0)
