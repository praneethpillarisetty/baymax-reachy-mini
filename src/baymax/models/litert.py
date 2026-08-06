from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ..contracts import ModelResponse
from ..core.toml import TOMLDecodeError, load_toml
from .base import parse_model_response


class UnsupportedModelError(RuntimeError):
    pass


class Tokenizer(Protocol):
    def encode(self, text: str) -> Any: ...
    def decode(self, tokens: Any) -> str: ...


class LiteRTRunner(Protocol):
    def inspect_signatures(self) -> dict[str, Any]: ...
    def generate(self, system_prompt: str, text: str) -> str: ...


@dataclass(frozen=True)
class LiteRTProfile:
    id: str
    display_name: str
    model_path: str
    tokenizer_path: str
    runtime: str
    architecture: str
    quantization: str
    max_context: int
    platform: str
    input_signature: dict[str, Any] | None = None
    output_signature: dict[str, Any] | None = None

    @classmethod
    def load(cls, path: Path) -> "LiteRTProfile":
        try:
            profile = cls(**load_toml(path))
        except (OSError, TOMLDecodeError, TypeError) as exc:
            raise ValueError(f"invalid LiteRT profile: {path}") from exc
        if not profile.id or profile.runtime != "litert" or profile.max_context < 1:
            raise ValueError("profile requires an id, LiteRT runtime, and positive context")
        return profile

    def resolve_files(self, profile_path: Path) -> tuple[Path, Path]:
        root = profile_path.parent
        return (root / self.model_path).resolve(), (root / self.tokenizer_path).resolve()


class LiteRTModel:
    """Generic shell. Inference stays fail-closed without an exact artifact runner."""

    def __init__(
        self,
        profile_path: Path,
        runner: LiteRTRunner | None = None,
        dry_run: bool = False,
        model_path_override: Path | None = None,
    ):
        self.profile_path = profile_path
        self.profile = LiteRTProfile.load(profile_path)
        self.model_path, self.tokenizer_path = self.profile.resolve_files(profile_path)
        if model_path_override is not None:
            self.model_path = model_path_override.resolve()
        if not dry_run:
            if not self.model_path.is_file():
                raise FileNotFoundError(f"LiteRT model missing: {self.model_path}")
            if not self.tokenizer_path.exists():
                raise FileNotFoundError(f"tokenizer missing: {self.tokenizer_path}")
        self.runner = runner

    def inspect_signatures(self) -> dict[str, Any]:
        if self.runner:
            return self.runner.inspect_signatures()
        if self.profile.input_signature is not None and self.profile.output_signature is not None:
            return {"input": self.profile.input_signature, "output": self.profile.output_signature}
        raise UnsupportedModelError("No signature metadata or exact LiteRT runner is available")

    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        if self.runner is None:
            raise UnsupportedModelError(
                f"No verified LiteRT runner registered for architecture {self.profile.architecture!r}"
            )
        return parse_model_response(self.runner.generate(system_prompt, text))
