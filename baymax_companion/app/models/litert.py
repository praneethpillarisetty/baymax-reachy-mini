from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from ..contracts import ModelResponse
from .base import parse_model_response


@dataclass(frozen=True)
class LiteRTProfile:
    model_identifier: str
    model_path: str
    tokenizer_path: str
    input_signature: dict[str, Any]
    output_signature: dict[str, Any]
    quantization: str
    expected_memory_mb: int
    supported_context_length: int
    expected_platform: str

    @classmethod
    def load(cls, path: Path) -> "LiteRTProfile":
        try:
            data = json.loads(path.read_text())
            profile = cls(**data)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"invalid LiteRT profile: {path}") from exc
        if (
            not profile.input_signature
            or not profile.output_signature
            or profile.supported_context_length < 1
        ):
            raise ValueError("LiteRT profile signatures and context length are required")
        return profile


class LiteRTModel:
    """Model-neutral shell; a profile-specific runner owns tokenization and tensors."""

    def __init__(
        self, model_path: Path, profile_path: Path, runner: Callable[..., str] | None = None
    ):
        if not model_path.is_file():
            raise FileNotFoundError(model_path)
        self.profile = LiteRTProfile.load(profile_path)
        self.model_path, self.runner = model_path, runner

    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        if self.runner is None:
            raise RuntimeError("No model-profile LiteRT runner is installed")
        return parse_model_response(self.runner(self.model_path, self.profile, system_prompt, text))
