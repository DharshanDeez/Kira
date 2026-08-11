"""Quick scan: which input device picks up audio."""
from __future__ import annotations

import time

import numpy as np
import sounddevice as sd

print("Scanning microphones — speak during each 2s test...\n")
best_idx, best_peak = None, 0.0

for i, dev in enumerate(sd.query_devices()):
    if dev["max_input_channels"] < 1:
        continue
    peaks: list[float] = []

    def callback(indata, frames, time_info, status) -> None:  # noqa: ARG001
        peaks.append(float(np.max(np.abs(indata))))

    try:
        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype="float32",
            device=i,
            blocksize=1600,
            callback=callback,
        ):
            time.sleep(2.0)
        peak = max(peaks) if peaks else 0.0
    except Exception as exc:
        print(f"  [{i}] ERROR — {dev['name'][:50]}: {exc}")
        continue

    tag = ""
    if peak > best_peak:
        best_peak = peak
        best_idx = i
        tag = "  <-- best so far"
    print(f"  [{i}] peak {peak:.0%} — {dev['name'][:55]}{tag}")

print(f"\nRecommended: input_device: {best_idx}  (peak {best_peak:.0%})")
