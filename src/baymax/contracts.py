from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ActionRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    message: str
    actions: tuple[ActionRequest, ...] = ()
    emotion: str = "neutral"
    backend: str = "unknown"
    fallback_reason: str | None = None


class ConversationModel(Protocol):
    def health_check(self) -> tuple[bool, str]: ...
    def generate(self, text: str, system_prompt: str) -> ModelResponse: ...
    def cancel(self) -> None: ...


class Robot(Protocol):
    def connect(self) -> None: ...
    def start(self) -> None: ...
    def express(self, emotion: str) -> None: ...
    def stop_motion(self) -> None: ...
    def shutdown(self) -> None: ...
    def status(self) -> dict[str, Any]: ...


class SpeechToText(Protocol):
    def listen(self) -> str: ...


class TextToSpeech(Protocol):
    def speak(self, text: str) -> None: ...
