"""Speech-to-text via faster-whisper (local, models on D: drive)."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

# Common Whisper hallucinations on silence / short clips
_HALLUCINATION_PHRASES = (
    "thank you",
    "thanks for watching",
    "subscribe",
    "please subscribe",
    "bye",
    "you",
)


class SpeechToText:
    def __init__(
        self,
        model_size: str,
        models_dir: Path,
        device: str = "auto",
        compute_type: str = "auto",
        user_name: str = "the user",
    ) -> None:
        if device == "auto":
            device = "cuda" if _has_cuda() else "cpu"
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        self._user_name = user_name
        self._model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(models_dir),
        )
        print(f"  STT: whisper-{model_size} on {device} ({compute_type})")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if audio.size == 0:
            return ""

        peak = float(np.max(np.abs(audio)))
        if peak < 1e-5:
            return ""

        segments, _ = self._model.transcribe(
            audio,
            language="en",
            beam_size=5,
            best_of=5,
            temperature=0.0,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 300,
                "speech_pad_ms": 200,
                "threshold": 0.5,
            },
            condition_on_previous_text=False,
            initial_prompt=(
                f"The speaker is {self._user_name}, giving a command to voice assistant Kira."
            ),
        )
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        text = " ".join(parts).strip()
        return clean_transcript(text)


def clean_transcript(text: str) -> str:
    """Remove wake phrase prefix and known Whisper hallucinations."""
    if not text:
        return ""

    text = re.sub(r"^(hey|hi|ok|okay|hay)\s*k(iy|ai)?r+a[,.\s]*", "", text, flags=re.I)
    text = text.strip(" ,.")

    if is_hallucination(text):
        return ""

    return text.strip()


def is_hallucination(text: str) -> bool:
    lower = text.lower().strip()
    if not lower:
        return True

    for phrase in _HALLUCINATION_PHRASES:
        if lower.count(phrase) >= 2:
            return True
        if lower == phrase or lower == phrase + ".":
            return True

    words = lower.replace(".", "").split()
    if len(words) >= 6:
        unique = len(set(words))
        if unique <= 2:
            return True

    return False


def _has_cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False
