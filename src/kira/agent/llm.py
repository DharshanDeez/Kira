"""Local LLM via Ollama (qwen2.5:7b)."""

from __future__ import annotations

import ollama

from kira.agent.prompts import build_system_prompt


class OllamaBrain:
    def __init__(
        self,
        model: str,
        base_url: str,
        user_name: str = "there",
    ) -> None:
        self.model = model
        self._client = ollama.Client(host=base_url)
        self._system = build_system_prompt(user_name)
        self._history: list[dict[str, str]] = []
        self._max_history = 6  # last 3 exchanges

    def check_connection(self) -> None:
        """Raise if Ollama is not reachable or model missing."""
        listed = self._client.list()
        names = [m.model for m in listed.models]
        # ollama returns names like "qwen2.5:7b" or with digest prefix
        if not any(self.model in n for n in names):
            raise RuntimeError(
                f"Model {self.model!r} not found in Ollama. "
                f"Run: ollama pull {self.model}"
            )

    def chat(self, user_message: str) -> str:
        messages = [{"role": "system", "content": self._system}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_message})

        response = self._client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": 0.7, "num_predict": 150},
        )
        reply = response.message.content.strip()
        if not reply:
            return "I'm not sure how to answer that."

        self._history.append({"role": "user", "content": user_message})
        self._history.append({"role": "assistant", "content": reply})
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        return reply

    def clear_history(self) -> None:
        self._history = []
