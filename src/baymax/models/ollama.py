from __future__ import annotations

import json
import time
from urllib import error, request

from ..contracts import ModelResponse
from .base import parse_model_response


class OllamaConnectionError(RuntimeError):
    pass


class OllamaModel:
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

    def _request(self, path: str, body: bytes | None = None) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            req = request.Request(f"{self.url}{path}", body, {"Content-Type": "application/json"})
            try:
                with request.urlopen(req, timeout=self.timeout) as response:
                    value = json.loads(response.read())
                    if not isinstance(value, dict):
                        raise TypeError("Ollama response is not an object")
                    return value
            except (error.URLError, TimeoutError, json.JSONDecodeError, TypeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(0.1 * (2**attempt), 1.0))
        raise OllamaConnectionError(
            f"Could not reach Ollama at {self.url} after {self.retries + 1} attempt(s)"
        ) from last_error

    def health_check(self) -> tuple[bool, str]:
        try:
            result = self._request("/api/tags")
        except OllamaConnectionError as exc:
            return False, str(exc)
        models = result.get("models", [])
        names = (
            [item.get("name", "") for item in models if isinstance(item, dict)]
            if isinstance(models, list)
            else []
        )
        if self.model not in names:
            return (
                False,
                f"Ollama is reachable but configured model {self.model!r} is not installed",
            )
        return True, f"Ollama is reachable and configured model {self.model!r} is installed"

    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                "options": {"num_ctx": self.context_length, "temperature": self.temperature},
            }
        ).encode()
        result = self._request("/api/chat", body)
        try:
            return parse_model_response(result["message"]["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Ollama returned an invalid structured response") from exc
