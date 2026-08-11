"""Microphone capture and speaker playback."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

import numpy as np
import sounddevice as sd


def list_input_devices() -> None:
    """Print input devices — use index in config.yaml voice.input_device."""
    print("\n--- Microphone devices (input only) ---\n")
    default_in, _ = sd.default.device
    for label, idx in get_input_device_choices():
        dev = sd.query_devices(idx)
        marker = "  <- Windows default" if idx == default_in else ""
        print(f"  {label}{marker}")
        print(f"       {dev['max_input_channels']} ch, {dev['default_samplerate']:.0f} Hz")
    print("\nSet voice.input_device in config.yaml to the best index.")
    print("WASAPI devices (often clearer on Windows) usually say 'WASAPI' in the name.\n")


def get_input_device_choices() -> list[tuple[str, int | None]]:
    """Return (label, device_index) pairs for GUI / config."""
    default_in, _ = sd.default.device
    choices: list[tuple[str, int | None]] = []
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] < 1:
            continue
        name = dev["name"].strip()
        if len(name) > 42:
            name = name[:39] + "..."
        marker = " *" if i == default_in else ""
        choices.append((f"[{i}] {name}{marker}", i))
    return choices


def peak_level(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.max(np.abs(audio)))


def normalize_audio(audio: np.ndarray, target_peak: float = 0.85) -> np.ndarray:
    """Boost quiet mic input so Whisper hears you clearly."""
    if audio.size == 0:
        return audio
    peak = peak_level(audio)
    if peak < 1e-6:
        return audio
    if peak < 0.25:
        audio = audio * (target_peak / peak)
    return np.clip(audio, -1.0, 1.0)


def monitor_mic_level(device: int | None, sample_rate: int, seconds: float = 3.0) -> float:
    """Show live mic level bar; return peak seen (0-1)."""
    peak_seen = 0.0
    block = int(sample_rate * 0.1)

    def callback(indata, frames, time_info, status) -> None:  # noqa: ARG002
        nonlocal peak_seen
        peak_seen = max(peak_seen, peak_level(indata))

    print("Speak normally — watching mic level:")
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        device=device,
        blocksize=block,
        callback=callback,
    ):
        elapsed = 0.0
        while elapsed < seconds:
            bar_len = int(min(peak_seen, 1.0) * 30)
            bar = "#" * bar_len + "-" * (30 - bar_len)
            print(f"\r  [{bar}] {peak_seen:.0%}  ", end="", flush=True)
            sd.sleep(100)
            elapsed += 0.1
    print(f"\r  peak: {peak_seen:.0%}  ", end="")
    if peak_seen < 0.05:
        print("\n  WARNING: Very quiet — check mic permissions or try another input_device.")
    elif peak_seen < 0.15:
        print("\n  Tip: Speak closer to the mic or raise Windows input volume.")
    else:
        print("\n  Mic level looks good.")
    print()
    return peak_seen


class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._recording = False

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        if self._recording:
            self._frames.append(indata.copy())

    def start(self) -> None:
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._frames:
            return np.array([], dtype=np.float32)
        audio = np.concatenate(self._frames, axis=0).flatten()
        return normalize_audio(audio)

    def record_for_seconds(self, seconds: float) -> np.ndarray:
        self.start()
        sd.sleep(int(seconds * 1000))
        return self.stop()


def play_audio(samples: np.ndarray, sample_rate: int) -> None:
    if samples.size == 0:
        return
    sd.play(samples, sample_rate)
    sd.wait()


def stop_speech() -> None:
    """Stop any audio currently playing through the speakers."""
    sd.stop()


def play_wav_file(path: str) -> None:
    from scipy.io import wavfile

    rate, data = wavfile.read(path)
    if data.dtype != np.float32:
        if data.dtype == np.int16:
            data = data.astype(np.float32) / 32768.0
        else:
            data = data.astype(np.float32)
    if data.ndim > 1:
        data = data.mean(axis=1)
    play_audio(data, rate)


def run_while_key_held(
    hotkey: str,
    on_start: Callable[[], None],
    on_stop: Callable[[], None],
    poll_interval: float = 0.05,
) -> None:
    """Poll hotkey; call on_start when pressed, on_stop when released."""
    import keyboard

    held = False
    while True:
        pressed = keyboard.is_pressed(hotkey)
        if pressed and not held:
            held = True
            on_start()
        elif not pressed and held:
            held = False
            on_stop()
        sd.sleep(int(poll_interval * 1000))


class ContinuousMic:
    """
    Always-on mic capture in a background callback so Whisper wake checks
    don't block reading audio (which caused missed 'Hey Kira').
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        device: int | None = None,
        ring_seconds: float = 4.0,
        blocksize: int = 1280,
    ) -> None:
        self.sample_rate = sample_rate
        self.device = device
        self.blocksize = blocksize
        self._max_samples = int(sample_rate * ring_seconds)
        self._ring: deque[np.ndarray] = deque()
        self._ring_samples = 0
        self._command: list[np.ndarray] = []
        self._recording = False
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._last_rms = 0.0

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        chunk = indata[:, 0].copy()
        rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
        with self._lock:
            self._last_rms = rms
            self._ring.append(chunk)
            self._ring_samples += len(chunk)
            while self._ring_samples > self._max_samples and self._ring:
                self._ring_samples -= len(self._ring.popleft())
            if self._recording:
                self._command.append(chunk)

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device,
            blocksize=self.blocksize,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @property
    def last_rms(self) -> float:
        with self._lock:
            return self._last_rms

    def get_recent(self, seconds: float) -> np.ndarray:
        want = int(self.sample_rate * seconds)
        with self._lock:
            if not self._ring:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(list(self._ring))
        return audio[-want:] if len(audio) > want else audio

    def begin_command(self, prefix: np.ndarray | None = None) -> None:
        with self._lock:
            self._command = []
            if prefix is not None and prefix.size:
                self._command.append(prefix.copy())
            self._recording = True

    def end_command(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            if not self._command:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._command)

    def wait_seconds(self, seconds: float) -> None:
        time.sleep(seconds)

