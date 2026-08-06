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


class ConversationModel(Protocol):
    def generate(self, text: str, system_prompt: str) -> ModelResponse: ...


class Robot(Protocol):
    def start(self) -> None: ...
    def express(self, emotion: str) -> None: ...
    def stop_motion(self) -> None: ...
    def shutdown(self) -> None: ...


class SpeechToText(Protocol):
    def listen(self) -> str: ...


class TextToSpeech(Protocol):
    def speak(self, text: str) -> None: ...
