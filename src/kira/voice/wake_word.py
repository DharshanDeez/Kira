"""Wake word detection — 'Hey Kira'."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel


def _normalize(audio: np.ndarray) -> np.ndarray:
    audio = audio.astype(np.float32)
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak > 1e-6 and peak < 0.3:
        audio = audio * (0.85 / peak)
    return np.clip(audio, -1.0, 1.0)


def _rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))


def peak_block_rms(audio: np.ndarray, block: int = 1600) -> float:
    """Loudest short slice — better than mean RMS for brief 'Hey Kira'."""
    if audio.size == 0:
        return 0.0
    block = min(block, len(audio))
    best = 0.0
    step = max(block // 2, 1)
    for start in range(0, len(audio) - block + 1, step):
        best = max(best, _rms(audio[start : start + block]))
    return best


def best_wake_segment(
    audio: np.ndarray, sample_rate: int = 16000, seconds: float = 1.6
) -> np.ndarray:
    """Pick the loudest slice for wake-word STT (short phrase in a long window)."""
    want = int(sample_rate * seconds)
    if len(audio) <= want:
        return audio
    block = int(sample_rate * 0.1)
    best_start = 0
    best_rms = 0.0
    step = max(block // 2, 1)
    for start in range(0, len(audio) - want + 1, step):
        chunk = audio[start : start + want]
        level = peak_block_rms(chunk, block=block)
        if level > best_rms:
            best_rms = level
            best_start = start
    return audio[best_start : best_start + want]


class WakeWordDetector(ABC):
    @abstractmethod
    def check(self, audio: np.ndarray, sample_rate: int = 16000) -> str | None:
        """Return wake phrase text if detected, else None."""


class WhisperWakeWordDetector(WakeWordDetector):
    """
    Detect 'Hey Kira' using Whisper tiny on short audio windows.
    Lightweight VAD gating keeps CPU use reasonable until custom openWakeWord model is added.
    """

    # Must include hey/hi/ok before kira — standalone "kira" no longer triggers wake
    WAKE_PATTERN = re.compile(
        r"\b(hey|hi|ok|okay|hay)\s*,?\s*k(iy|ai|e)?r+a\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        models_dir: Path,
        model_size: str = "tiny",
        device: str = "auto",
        compute_type: str = "auto",
        min_rms: float = 0.008,
    ) -> None:
        if device == "auto":
            device = "cuda" if _has_cuda() else "cpu"
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        self.min_rms = min_rms
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(models_dir),
        )
        print(f"  Wake word: whisper-{model_size} listening for 'Hey Kira'")

    def check(self, audio: np.ndarray, sample_rate: int = 16000) -> str | None:
        """Return matched wake text, or None."""
        level = peak_block_rms(audio)
        if level < self.min_rms:
            return None
        clip = best_wake_segment(audio, sample_rate)
        clip = _normalize(clip)
        segments, _ = self._model.transcribe(
            clip,
            language="en",
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
            initial_prompt="Hey Kira. Wake word.",
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        if not text:
            return None
        if self.WAKE_PATTERN.search(text):
            return text
        # Fuzzy: Whisper often hears "Kira" / "Kyra" with hey/hi nearby
        lower = text.lower()
        if ("kira" in lower or "kyra" in lower or "keera" in lower or "kara" in lower) and any(
            w in lower for w in ("hey", "hi", "ok", "okay", "hay", "here")
        ):
            return text
        return None


class OpenWakeWordDetector(WakeWordDetector):
    """Use a custom .onnx wake word model (e.g. hey_kira.onnx after training)."""

    def __init__(self, model_path: Path, threshold: float = 0.5) -> None:
        from openwakeword.model import Model
        from openwakeword.utils import download_models

        if not model_path.exists():
            raise FileNotFoundError(f"Wake word model not found: {model_path}")
        download_models()
        self.threshold = threshold
        self._model = Model(
            wakeword_models=[str(model_path)],
            inference_framework="onnx",
            vad_threshold=0.3,
        )
        self._model_name = model_path.stem
        print(f"  Wake word: openWakeWord ({self._model_name})")

    def check(self, audio: np.ndarray, sample_rate: int = 16000) -> str | None:
        if audio.dtype != np.int16:
            pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        else:
            pcm = audio

        frame_size = 1280
        max_score = 0.0
        for start in range(0, len(pcm) - frame_size + 1, frame_size):
            frame = pcm[start : start + frame_size]
            scores = self._model.predict(frame)
            for score in scores.values():
                max_score = max(max_score, float(score))
        if max_score >= self.threshold:
            return self._model_name
        return None


def create_wake_detector(cfg: dict, models_dir: Path) -> WakeWordDetector:
    wake = cfg.get("wake_word", {})
    engine = wake.get("engine", "whisper")
    oww_path = models_dir / "openwakeword" / wake.get("openwakeword_model", "hey_kira.onnx")

    if engine == "openwakeword" and oww_path.exists():
        return OpenWakeWordDetector(oww_path, threshold=float(wake.get("threshold", 0.5)))

    voice = cfg.get("voice", {})
    return WhisperWakeWordDetector(
        models_dir=models_dir / "whisper",
        model_size=wake.get("whisper_model", "tiny"),
        device=voice.get("stt_device", "auto"),
        compute_type=voice.get("stt_compute_type", "auto"),
        min_rms=float(wake.get("min_rms", 0.008)),
    )


def _has_cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False
