"""Short listening chime when Kira wakes up."""

from __future__ import annotations

import numpy as np

from kira.voice.audio import play_audio


def play_wake_chime(sample_rate: int = 16000) -> None:
    """Two-tone chime — signals Kira is listening."""
    duration = 0.12
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone1 = 0.25 * np.sin(2 * np.pi * 880 * t)
    tone2 = 0.25 * np.sin(2 * np.pi * 1175 * t)
    gap = np.zeros(int(sample_rate * 0.04), dtype=np.float32)
    audio = np.concatenate([tone1.astype(np.float32), gap, tone2.astype(np.float32)])
    # Soft fade out
    fade = np.linspace(1.0, 0.0, min(400, len(audio)))
    audio[-len(fade) :] *= fade
    play_audio(audio, sample_rate)
