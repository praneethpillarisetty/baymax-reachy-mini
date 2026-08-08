import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from baymax.contracts import ModelResponse
from baymax.memory import LocalStore
from baymax.models.mock import MockModel
from baymax.orchestrator import ConversationOrchestrator
from baymax.robot.simulator import SimulatorRobot
from baymax.safety import SafetyEngine
from baymax.tools import ToolExecutor
from baymax.ui import create_handler
from baymax.voice.tts import ConsoleTTS


class FakeApp:
    def handle(self, text: str) -> ModelResponse:
        return ModelResponse(f"Safe reply to {text}")


def test_local_ui_get_and_conversation():
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(FakeApp()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        with urlopen(url, timeout=2) as response:
            assert b"Baymax Companion" in response.read()
        request = Request(
            url,
            data=urlencode({"message": "<hello>"}).encode(),
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            body = response.read()
            assert b"Safe reply to &lt;hello&gt;" in body
            assert b"Safe reply to <hello>" not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request(url: str, path: str, payload: dict[str, object] | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url + path,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST" if data else "GET",
    )
    with urlopen(request, timeout=2) as response:
        return json.loads(response.read())


def test_ui_api_health_safety_and_wellness(tmp_path: Path):
    robot = SimulatorRobot()
    robot.start()
    app = ConversationOrchestrator(
        MockModel(),
        SafetyEngine(),
        ToolExecutor(LocalStore(tmp_path / "ui.sqlite3")),
        robot,
        ConsoleTTS(),
        "test",
    )
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_handler(app, backend="mock", mode="simulator")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        health = _request(url, "/api/health")
        assert health["bind_host"] == "127.0.0.1"
        assert health["backend"] == "mock"
        assert health["voice"] == "mock"
        assert health["robot"]["backend"] == "simulator"
        assert _request(url, "/api/message", {"message": "hello"})["result"].startswith(
            "I hear you"
        )
        emergency = _request(url, "/api/message", {"message": "I have chest pain"})["result"]
        assert "emergency services" in emergency
        assert (
            "created"
            in _request(url, "/api/reminders", {"title": "stretch", "when": "18:00"})["result"]
        )
        assert "stretch" in _request(url, "/api/reminders")["result"]
        assert "logged" in _request(url, "/api/mood", {"mood": "calm"})["result"]
        assert "logged" in _request(url, "/api/hydration", {"milliliters": 250})["result"]
        summary = _request(url, "/api/wellness")["result"]
        assert "mood: 1" in summary and "hydration_ml: 1" in summary
        assert _request(url, "/api/safe-stop", {})["result"] == "Safe stop engaged"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
