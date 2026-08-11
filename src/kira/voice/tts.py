"""Text-to-speech via Piper (local binary + models on D: drive)."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from kira.voice.audio import play_wav_file


class TextToSpeech:
    def __init__(self, piper_dir: Path, voice_name: str) -> None:
        self.piper_exe = piper_dir / "piper.exe"
        self.model_path = piper_dir / f"{voice_name}.onnx"
        self.config_path = piper_dir / f"{voice_name}.onnx.json"
        self._validate()

    def _validate(self) -> None:
        missing = [
            p for p in (self.piper_exe, self.model_path, self.config_path) if not p.exists()
        ]
        if missing:
            names = ", ".join(p.name for p in missing)
            raise FileNotFoundError(
                f"Piper assets missing ({names}). Run: python -m kira setup"
            )

    def synthesize_to_file(self, text: str, output_wav: Path) -> Path:
        if not text.strip():
            return output_wav
        cmd = [
            str(self.piper_exe),
            "--model",
            str(self.model_path),
            "--config",
            str(self.config_path),
            "--output_file",
            str(output_wav),
        ]
        subprocess.run(
            cmd,
            input=text,
            text=True,
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        return output_wav

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        from kira.voice.audio import stop_speech

        stop_speech()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)
        try:
            self.synthesize_to_file(text, wav_path)
            play_wav_file(str(wav_path))
        finally:
            wav_path.unlink(missing_ok=True)
