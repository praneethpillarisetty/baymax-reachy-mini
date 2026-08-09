from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path
from urllib import error, request

from ..contracts import ModelResponse
from ..tools import MODEL_ACTION_NAMES
from .base import parse_model_response


class OllamaConnectionError(RuntimeError):
    """An actionable failure at the local Ollama HTTP boundary."""


class OllamaModel:
    backend_name = "ollama"

    def __init__(
        self,
        url: str,
        model: str,
        timeout: float,
        context_length: int,
        temperature: float,
        retries: int = 2,
    ):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout
        self.context_length, self.temperature, self.retries = context_length, temperature, retries
        self.cancelled = threading.Event()

    @staticmethod
    def installation_status() -> tuple[bool, str]:
        executable = shutil.which("ollama")
        if executable:
            return True, f"Ollama executable found at {executable}"
        return False, (
            "Ollama is not installed or is not on PATH. Install it manually from "
            "https://ollama.com/download; Baymax never runs remote installer scripts."
        )

    def _request(self, path: str, body: bytes | None = None) -> dict[str, object]:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            if self.cancelled.is_set():
                raise OllamaConnectionError("Ollama request cancelled by safe stop")
            req = request.Request(f"{self.url}{path}", body, {"Content-Type": "application/json"})
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    if response.status != 200:
                        raise OllamaConnectionError(
                            f"Ollama returned HTTP {response.status}; check the server logs"
                        )
                    try:
                        value = json.loads(response.read())
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        raise OllamaConnectionError("Ollama returned malformed JSON") from exc
                    if not isinstance(value, dict):
                        raise OllamaConnectionError("Ollama JSON response is not an object")
                    return value
            except error.HTTPError as exc:
                raise OllamaConnectionError(
                    f"Ollama returned HTTP {exc.code}; check the model and server logs"
                ) from exc
            except (error.URLError, ConnectionError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(0.1 * (2**attempt), 1.0))
        detail = "timed out" if isinstance(last_error, TimeoutError) else "refused"
        raise OllamaConnectionError(
            f"Ollama connection {detail} at {self.url} after {self.retries + 1} attempt(s); "
            "start `ollama serve` and verify OLLAMA_URL"
        ) from last_error

    def installed_models(self) -> tuple[str, ...]:
        result = self._request("/api/tags")
        models = result.get("models")
        if not isinstance(models, list):
            raise OllamaConnectionError("Ollama /api/tags returned an invalid models field")
        return tuple(
            name
            for item in models
            if isinstance(item, dict)
            and isinstance((name := item.get("name", item.get("model"))), str)
        )

    def health_check(self, *, test_chat: bool = False) -> tuple[bool, str]:
        try:
            names = self.installed_models()
            if self.model not in names:
                return False, (
                    f"Ollama is reachable but {self.model!r} is not installed; installed: "
                    f"{', '.join(names) or '(none)'}. Run `ollama pull {self.model}` after reviewing it."
                )
            if test_chat:
                result = self._request(
                    "/api/chat",
                    json.dumps(
                        {
                            "model": self.model,
                            "stream": False,
                            "messages": [{"role": "user", "content": "Reply with the word ready."}],
                            "options": {"num_predict": 8},
                        }
                    ).encode(),
                )
                message = result.get("message")
                if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                    return False, "Ollama /api/chat returned invalid model output"
        except OllamaConnectionError as exc:
            return False, str(exc)
        checks = "is installed and passed bounded chat checks" if test_chat else "is installed"
        return True, f"Ollama model {self.model!r} {checks}"

    def verify_and_store(self, destination: Path) -> None:
        ok, detail = self.health_check(test_chat=True)
        if not ok:
            raise OllamaConnectionError(detail)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps({"url": self.url, "model": self.model}), encoding="utf-8")
        temporary.replace(destination)

    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        self.cancelled.clear()
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "emotion": {"type": "string"},
                        "actions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "tool": {
                                        "type": "string",
                                        "enum": list(MODEL_ACTION_NAMES),
                                    },
                                    "arguments": {"type": "object"},
                                },
                                "required": ["tool"],
                            },
                        },
                    },
                    "required": ["message"],
                },
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                        + " Respond only with a JSON object containing a string 'message', "
                        "an optional supported 'emotion', and an optional 'actions' array. "
                        "Do not request an action unless it is necessary for the user's request. "
                        "The breath action is a harmless no-op available only in simulator mode.",
                    },
                    {"role": "user", "content": text},
                ],
                "options": {"num_ctx": self.context_length, "temperature": self.temperature},
            }
        ).encode()
        result = self._request("/api/chat", body)
        try:
            message = result["message"]
            if not isinstance(message, dict):
                raise TypeError("message is not an object")
            return parse_model_response(message["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Ollama returned invalid structured JSON") from exc

    def cancel(self) -> None:
        """Prevent retries; urllib cannot abort an already-running socket portably."""
        self.cancelled.set()
