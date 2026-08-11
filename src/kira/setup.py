"""Download Piper + Whisper assets to D:\\cofounder\\models."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import httpx

from kira.config import load_config

PIPER_RELEASE = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# voice_id -> path under rhasspy/piper-voices
PIPER_VOICES: dict[str, str] = {
    "en_US-lessac-medium": "en/en_US/lessac/medium",          # female, US, natural
    "en_US-amy-medium": "en/en_US/amy/medium",                # female, US
    "en_GB-jenny_dioco-medium": "en/en_GB/jenny_dioco/medium",  # female, British (Kira default)
    "en_GB-alan-medium": "en/en_GB/alan/medium",              # male, British
}


def _voice_urls(voice_id: str) -> tuple[str, str]:
    rel = PIPER_VOICES.get(voice_id)
    if not rel:
        known = ", ".join(sorted(PIPER_VOICES))
        raise ValueError(f"Unknown piper_voice {voice_id!r}. Choose one of: {known}")
    base = f"{HF_BASE}/{rel}"
    return f"{base}/{voice_id}.onnx", f"{base}/{voice_id}.onnx.json"


def _download(url: str, dest: Path, client: httpx.Client) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  skip (exists): {dest.name}")
        return
    print(f"  download: {dest.name}")
    with client.stream("GET", url, follow_redirects=True, timeout=120) as resp:
        resp.raise_for_status()
        with dest.open("wb") as f:
            for chunk in resp.iter_bytes(65536):
                f.write(chunk)


def _extract_piper_bundle(zip_path: Path, dest_dir: Path) -> None:
    """Extract full Piper release (exe + DLLs + espeak data) into dest_dir."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        prefix = "piper/"
        for name in zf.namelist():
            if not name.startswith(prefix) or name.endswith("/"):
                continue
            relative = name[len(prefix) :]
            target = dest_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)

    if not (dest_dir / "piper.exe").exists():
        raise RuntimeError("piper.exe not found after extraction")


def download_piper_voice(voice_id: str, piper_dir: Path, client: httpx.Client) -> None:
    onnx_url, json_url = _voice_urls(voice_id)
    _download(onnx_url, piper_dir / f"{voice_id}.onnx", client)
    _download(json_url, piper_dir / f"{voice_id}.onnx.json", client)


def setup_models() -> None:
    cfg = load_config()
    models_dir = cfg["_paths"]["models"]
    piper_dir = models_dir / "piper"
    piper_dir.mkdir(parents=True, exist_ok=True)
    (models_dir / "whisper").mkdir(parents=True, exist_ok=True)

    voice_id = cfg.get("voice", {}).get("piper_voice", "en_GB-jenny_dioco-medium")
    user_name = cfg.get("user", {}).get("name", "the user")

    print(f"Kira model setup -> {models_dir}\n")

    with httpx.Client() as client:
        piper_exe = piper_dir / "piper.exe"
        if not piper_exe.exists() or not (piper_dir / "onnxruntime.dll").exists():
            zip_path = piper_dir / "piper.zip"
            print("Piper binary:")
            _download(PIPER_RELEASE, zip_path, client)
            print("  extracting piper bundle (exe + dlls) ...")
            _extract_piper_bundle(zip_path, piper_dir)
            zip_path.unlink(missing_ok=True)
        else:
            print("Piper binary: skip (exists)")

        print(f"Piper voice ({voice_id}):")
        download_piper_voice(voice_id, piper_dir, client)

    voice = cfg.get("voice", {})
    whisper_dir = models_dir / "whisper"
    model_size = voice.get("stt_model", "small")
    size_hint = "~500 MB" if model_size == "small" else "~150 MB"
    print(f"\nWhisper STT model ({model_size}, {size_hint} one-time download):")
    print("  Please wait 1-3 minutes...")
    from kira.voice.stt import SpeechToText

    SpeechToText(
        model_size=model_size,
        models_dir=whisper_dir,
        device=voice.get("stt_device", "auto"),
        compute_type=voice.get("stt_compute_type", "auto"),
        user_name=user_name,
    )
    print("  Whisper ready.")

    wake = cfg.get("wake_word", {})
    wake_model = wake.get("whisper_model", "tiny")
    if wake_model != model_size:
        print(f"\nWhisper wake-word model ({wake_model}):")
        from kira.voice.wake_word import WhisperWakeWordDetector

        WhisperWakeWordDetector(
            models_dir=whisper_dir,
            model_size=wake_model,
            device=voice.get("stt_device", "auto"),
            compute_type=voice.get("stt_compute_type", "auto"),
        )
        print("  Wake-word model ready.")

    oww_dir = models_dir / "openwakeword"
    oww_dir.mkdir(parents=True, exist_ok=True)
    print("\nopenWakeWord backbone (for future custom hey_kira.onnx):")
    try:
        from openwakeword.utils import download_models

        download_models()
        print("  openWakeWord models cached in package (optional upgrade path).")
    except Exception as exc:
        print(f"  skip: {exc}")

    print("\nDone. Run: .\\run.ps1 listen")
