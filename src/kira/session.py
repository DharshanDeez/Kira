"""Shared voice session — STT, TTS, LLM, recorder config."""

from __future__ import annotations

from kira.agent.llm import OllamaBrain
from kira.config import load_config, parse_input_device
from kira.tools.filesystem import FileSandbox
from kira.tools.filesystem_intent import FileCommandHandler
from kira.tools.reminder import ReminderStore
from kira.tools.reminder_intent import try_handle_reminder
from kira.voice.audio import AudioRecorder
from kira.voice.stt import SpeechToText
from kira.voice.tts import TextToSpeech


class VoiceSession:
    """Loads config and voice models used by push-to-talk and wake-word modes."""

    def __init__(self) -> None:
        self.cfg = load_config()
        self.paths = self.cfg["_paths"]
        voice = self.cfg.get("voice", {})
        llm = self.cfg.get("llm", {})
        self.sample_rate = int(voice.get("sample_rate", 16000))
        self.max_seconds = float(voice.get("record_seconds_max", 15))
        self.hotkey = self.cfg.get("hotkey", {}).get("push_to_talk", "ctrl+shift+k")
        self.user_name = self.cfg.get("user", {}).get("name", "there")
        self.input_device = parse_input_device(voice.get("input_device"))

        db_name = self.cfg.get("reminders", {}).get("database", "memory.db")
        self.reminders = ReminderStore(self.paths["data"] / db_name)

        fs_cfg = self.cfg.get("filesystem", {})
        roots = fs_cfg.get("allowed_roots") or ["~/Desktop", "~/Documents", "~/Downloads"]
        self.files = FileCommandHandler(FileSandbox(roots))

        piper_dir = self.paths["models"] / "piper"
        self.tts = TextToSpeech(
            piper_dir, voice.get("piper_voice", "en_GB-jenny_dioco-medium")
        )
        self._stt: SpeechToText | None = None
        self._stt_kwargs = dict(
            model_size=voice.get("stt_model", "small"),
            models_dir=self.paths["models"] / "whisper",
            device=voice.get("stt_device", "auto"),
            compute_type=voice.get("stt_compute_type", "auto"),
            user_name=self.user_name,
        )
        self._brain: OllamaBrain | None = None
        self._brain_kwargs = dict(
            model=llm.get("model", "qwen2.5:7b"),
            base_url=llm.get("base_url", "http://localhost:11434"),
            user_name=self.user_name,
        )
        self.recorder = AudioRecorder(
            sample_rate=self.sample_rate,
            device=self.input_device,
        )

    @property
    def stt(self) -> SpeechToText:
        if self._stt is None:
            print("Loading speech recognition model...")
            self._stt = SpeechToText(**self._stt_kwargs)
        return self._stt

    @property
    def brain(self) -> OllamaBrain:
        if self._brain is None:
            print(f"Connecting to Ollama ({self._brain_kwargs['model']})...")
            self._brain = OllamaBrain(**self._brain_kwargs)
            self._brain.check_connection()
            print(f"  Ollama ready: {self._brain_kwargs['model']}")
        return self._brain

    def respond(self, text: str, *, speak: bool = True) -> str:
        """Process user text; optionally speak the reply. Returns reply text."""
        if not text:
            msg = "Sorry, I couldn't understand that."
            if speak:
                self.tts.speak(msg)
            return msg

        # Pending file delete confirmation takes priority.
        if self.files.has_pending():
            handled, reply = self.files.try_handle(text)
            print(f"Kira: {reply}")
            if speak:
                self.tts.speak(reply)
            return reply

        handled, reply = try_handle_reminder(text, self.reminders)
        if handled:
            print(f"Kira: {reply}")
            if speak:
                self.tts.speak(reply)
            return reply

        from kira.tools.reminder_intent import looks_like_reminder_attempt, normalize_reminder_text

        if looks_like_reminder_attempt(normalize_reminder_text(text)):
            msg = (
                "I couldn't save that reminder. "
                "Say: remind me in 5 minutes to, then your task."
            )
            print(f"Kira: {msg}")
            if speak:
                self.tts.speak(msg)
            return msg

        handled, reply = self.files.try_handle(text)
        if handled:
            print(f"Kira: {reply}")
            if speak:
                self.tts.speak(reply)
            return reply

        from kira.tools.filesystem_intent import looks_like_filesystem_attempt

        if looks_like_filesystem_attempt(text):
            msg = (
                "I couldn't run that file command. "
                "Try: create folder testkira on desktop, "
                "or list files on desktop."
            )
            print(f"Kira: {msg}")
            if speak:
                self.tts.speak(msg)
            return msg

        print("Thinking...")
        try:
            reply = self.brain.chat(text)
        except Exception as exc:
            print(f"Ollama error: {exc}")
            reply = "I couldn't reach my language model. Is Ollama running?"
            if speak:
                self.tts.speak(reply)
            return reply
        print(f"Kira: {reply}")
        if speak:
            self.tts.speak(reply)
        return reply
