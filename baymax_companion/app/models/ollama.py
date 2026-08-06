from __future__ import annotations

import json
from urllib import error, request

from ..contracts import ModelResponse
from .base import parse_model_response


class OllamaModel:
    def __init__(
        self, url: str, model: str, timeout: float, context_length: int, temperature: float
    ):
        self.url, self.model, self.timeout = url.rstrip("/"), model, timeout
        self.context_length, self.temperature = context_length, temperature

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
        req = request.Request(f"{self.url}/api/chat", body, {"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read())
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("local Ollama request failed") from exc
        try:
            return parse_model_response(result["message"]["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Ollama returned an invalid structured response") from exc
