import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest

from baymax.contracts import ActionRequest, ModelResponse
from baymax.memory import LocalStore
from baymax.models.base import parse_model_response
from baymax.models.litert import LiteRTModel, LiteRTProfile
from baymax.models.mock import MockModel
from baymax.models.ollama import OllamaModel
from baymax.orchestrator import ConversationOrchestrator
from baymax.robot.simulator import SimulatorRobot
from baymax.safety import SafetyEngine
from baymax.tools import ToolExecutor
from baymax.voice.audio_pipeline import AudioPipeline
from baymax.voice.tts import MockTTS


class Broken:
    def generate(self, *_):
        raise RuntimeError("offline")


def app(tmp_path, model=None, fallback=None):
    robot, tts = SimulatorRobot(), MockTTS()
    robot.start()
    return ConversationOrchestrator(
        model or MockModel(),
        SafetyEngine(),
        ToolExecutor(LocalStore(tmp_path / "db.sqlite")),
        robot,
        tts,
        "kind",
        fallback,
    )


def test_normal_conversation(tmp_path):
    result = app(tmp_path).handle("hello")
    assert "hello" in result.message and result.emotion == "caring"


@pytest.mark.parametrize(
    "text",
    [
        "chest pain",
        "difficulty breathing",
        "stroke symptoms",
        "severe bleeding",
        "overdosed",
        "unconscious",
        "severe allergic reaction",
        "I might kill myself",
    ],
)
def test_emergency_bypasses_model(tmp_path, text):
    result = app(tmp_path, Broken()).handle(text)
    assert "emergency services" in result.message


def test_llm_failure_and_fallback(tmp_path):
    assert "trouble" in app(tmp_path, Broken()).handle("hello").message
    assert "hello" in app(tmp_path, Broken(), MockModel()).handle("hello").message


def test_prohibited_medical_advice_is_replaced(tmp_path):
    class Unsafe:
        def generate(self, *_):
            return ModelResponse("Increase your medication dosage.")

    assert "cannot diagnose" in app(tmp_path, Unsafe()).handle("question").message


def test_invalid_structured_output():
    with pytest.raises(ValueError):
        parse_model_response('{"actions": []}')
    with pytest.raises(ValueError):
        parse_model_response("{bad")


def test_ollama_timeout():
    model = OllamaModel("http://127.0.0.1:1", "x", 0.001, 32, 0)
    with patch("urllib.request.urlopen", side_effect=TimeoutError), pytest.raises(RuntimeError):
        model.generate("x", "x")


def test_ollama_health_requires_configured_model():
    model = OllamaModel("http://127.0.0.1:11434", "chosen:1b", 1, 32, 0, retries=0)
    with patch.object(model, "_request", return_value={"models": [{"name": "other:1b"}]}):
        available, detail = model.health_check()
    assert not available
    assert "not installed" in detail

    with patch.object(model, "_request", return_value={"models": [{"name": "chosen:1b"}]}):
        available, detail = model.health_check()
    assert available
    assert "is installed" in detail


def test_ollama_mock_server_tags_and_chat_contract():
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path == "/api/tags"
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"models":[{"model":"local:test"}]}')

        def do_POST(self):
            assert self.path == "/api/chat"
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(payload)
            self.send_response(200)
            self.end_headers()
            response = {"message": {"content": json.dumps({"message": "ok"})}}
            self.wfile.write(json.dumps(response).encode())

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        model = OllamaModel(f"http://127.0.0.1:{server.server_port}", "local:test", 1, 32, 0, 0)
        assert model.health_check()[0]
        assert model.generate("hello", "safe").message == "ok"
        assert seen[0]["stream"] is False and seen[0]["model"] == "local:test"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_reminder_create_failure_and_complete(tmp_path):
    tools = ToolExecutor(LocalStore(tmp_path / "d"))
    assert "created" in tools.execute(
        ActionRequest("create_reminder", {"title": "Water", "when": "soon"})
    )
    assert "Water" in tools.execute(ActionRequest("list_reminders"))
    assert "completed" in tools.execute(ActionRequest("complete_reminder", {"id": 1}))
    with pytest.raises(ValueError):
        tools.execute(ActionRequest("create_reminder", {}))
    with pytest.raises(ValueError):
        tools.execute(ActionRequest("shell", {"command": "rm"}))


def test_action_failure_is_truthful(tmp_path):
    class M:
        def generate(self, *_):
            return ModelResponse("Done", (ActionRequest("create_reminder", {}),))

    assert "Action failed" in app(tmp_path, M()).handle("x").message


def profile(tmp_path: Path):
    p = tmp_path / "p.toml"
    (tmp_path / "model.tflite").write_bytes(b"model")
    (tmp_path / "tokenizer").mkdir()
    p.write_text("""id = "x"
display_name = "Test"
model_path = "model.tflite"
tokenizer_path = "tokenizer"
runtime = "litert"
architecture = "test"
quantization = "int8"
max_context = 32
platform = "test"
[input_signature]
x = 1
[output_signature]
y = 1
""")
    return p


def test_missing_model_and_profile_validation(tmp_path):
    path = profile(tmp_path)
    (tmp_path / "model.tflite").unlink()
    with pytest.raises(FileNotFoundError):
        LiteRTModel(path)
    bad = tmp_path / "bad.toml"
    bad.write_text("id = 1")
    with pytest.raises(ValueError):
        LiteRTProfile.load(bad)


def test_litert_profile_neutral_runner(tmp_path):
    class Runner:
        def inspect_signatures(self):
            return {"input": {"x": 1}, "output": {"y": 1}}

        def generate(self, system_prompt, text):
            return '{"message":"ok","actions":[],"emotion":"neutral"}'

    adapter = LiteRTModel(profile(tmp_path), Runner())
    assert adapter.inspect_signatures()["input"]
    assert adapter.generate("x", "x").message == "ok"


def test_robot_stop_shutdown_and_unsafe_motion():
    r = SimulatorRobot()
    r.start()
    r.stop_motion()
    r.express("caring")
    assert "caring" not in r.events
    r.shutdown()
    assert not r.started
    with pytest.raises(ValueError):
        SimulatorRobot().express("spin_head_360")


def test_export_delete(tmp_path):
    store = LocalStore(tmp_path / "db")
    ToolExecutor(store).create_reminder({"title": "x", "when": "y"})
    out = tmp_path / "out"
    store.export(out)
    assert json.loads(out.read_text())["reminders"]
    store.delete_all()
    store.export(out)
    assert not json.loads(out.read_text())["reminders"]


def test_simulator_flow(tmp_path):
    a = app(tmp_path)
    a.handle("hello")
    assert a.robot.events == ["safe_start", "caring"]


def test_audio_adapter_failure():
    class BadASR:
        def listen(self):
            raise OSError

    with pytest.raises(RuntimeError):
        AudioPipeline(BadASR(), MockTTS()).receive()


def test_safe_stop_cancels_model_before_future_expressions(tmp_path):
    class Cancellable(MockModel):
        def __init__(self):
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    model = Cancellable()
    companion = app(tmp_path, model)
    companion.safe_stop()
    assert model.cancelled
    companion.handle("hello")
    assert "caring" not in companion.robot.events


def test_voice_and_robot_failures_preserve_text_response(tmp_path):
    class FailedOutput:
        def speak(self, text):
            raise OSError("speaker missing")

    class FailedRobot(SimulatorRobot):
        def express(self, emotion):
            raise RuntimeError("robot missing")

    robot = FailedRobot()
    robot.start()
    companion = ConversationOrchestrator(
        MockModel(), SafetyEngine(), ToolExecutor(LocalStore(tmp_path / "fail.sqlite")),
        robot, FailedOutput(), "kind",
    )
    assert "hello" in companion.handle("hello").message


def test_oversized_request_is_rejected_before_model(tmp_path):
    with pytest.raises(ValueError, match="1-4000"):
        app(tmp_path, Broken()).handle("x" * 4001)
