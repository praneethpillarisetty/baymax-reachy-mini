from __future__ import annotations

from pathlib import Path

from baymax.contracts import ModelResponse
from baymax.memory import LocalStore
from baymax.models.activation import ModelActivation
from baymax.models.registry import RuntimeModelRegistry
from baymax.orchestrator import ConversationOrchestrator
from baymax.robot.simulator import SimulatorRobot
from baymax.safety import SafetyEngine
from baymax.tools import ToolExecutor
from baymax.voice.audio_pipeline import AudioPipeline


class CountingModel:
    def __init__(self):
        self.calls = 0
        self.cancelled = False

    def generate(self, text: str, system_prompt: str) -> ModelResponse:
        self.calls += 1
        return ModelResponse(f"offline response: {text}", emotion="caring")

    def cancel(self) -> None:
        self.cancelled = True


class FakeASR:
    def __init__(self):
        self.cancelled = False

    def listen(self) -> str:
        return "hello from fake microphone"

    def cancel(self) -> None:
        self.cancelled = True


class FakeTTS:
    def __init__(self):
        self.messages: list[str] = []
        self.cancelled = False

    def speak(self, text: str) -> None:
        self.messages.append(text)

    def cancel(self) -> None:
        self.cancelled = True


def test_fake_voice_to_simulator_conversation_and_safe_stop(tmp_path):
    model, asr, tts, robot = CountingModel(), FakeASR(), FakeTTS(), SimulatorRobot()
    audio = AudioPipeline(asr, tts)
    robot.start()
    app = ConversationOrchestrator(
        model,
        SafetyEngine(),
        ToolExecutor(LocalStore(tmp_path / "e2e.sqlite3")),
        robot,
        tts,
        "offline test",
    )
    response = app.handle(audio.receive())
    assert response.message == "offline response: hello from fake microphone"
    assert robot.events[-1] == "caring"
    assert tts.messages == [response.message]
    app.safe_stop()
    audio.cancel()
    assert model.cancelled and tts.cancelled and asr.cancelled
    assert robot.stop_event.is_set()


def test_emergency_bypasses_model_and_uses_no_movement(tmp_path):
    model, tts, robot = CountingModel(), FakeTTS(), SimulatorRobot()
    robot.start()
    app = ConversationOrchestrator(
        model,
        SafetyEngine(),
        ToolExecutor(LocalStore(tmp_path / "emergency.sqlite3")),
        robot,
        tts,
        "offline test",
    )
    response = app.handle("I have chest pain")
    assert model.calls == 0
    assert "emergency services" in response.message
    assert "concern" not in robot.events


def test_model_activation_and_rollback_are_transactional(tmp_path):
    activation = ModelActivation(tmp_path, RuntimeModelRegistry(Path("config/model-registry.toml")))
    original = activation.activate({"llm": "mock-llm"})
    activation.activate({"llm": "mock-llm", "stt": ""})
    assert activation.rollback() == original
