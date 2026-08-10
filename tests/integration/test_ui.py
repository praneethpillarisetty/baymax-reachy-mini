import json
import hashlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from baymax.contracts import ModelResponse
from baymax.memory import LocalStore
from baymax.models.manager import ModelManager
from baymax.models.mock import MockModel
from baymax.orchestrator import ConversationOrchestrator
from baymax.robot.simulator import SimulatorRobot
from baymax.safety import SafetyEngine
from baymax.tools import ToolExecutor
from baymax.ui import create_handler
from baymax.voice.tts import ConsoleTTS
from baymax.voice.download import DownloadManager
from baymax.voice.setup import VoiceModelSetup


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
        assert health["asr_available"] is False
        assert health["asr_provider_selected"] is False
        assert health["asr_detail"] == "configured but real voice is disabled"
        assert health["tts_available"] is False
        assert health["tts_provider_selected"] is False
        assert health["tts_detail"] == "configured but real voice is disabled"
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


def test_setup_dashboard_and_progress_survive_refresh(tmp_path: Path):
    robot = SimulatorRobot()
    robot.start()
    app = ConversationOrchestrator(
        MockModel(),
        SafetyEngine(),
        ToolExecutor(LocalStore(tmp_path / "models.sqlite")),
        robot,
        ConsoleTTS(),
        "test",
    )
    manager = ModelManager(tmp_path / "data")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(app, model_manager=manager))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(url, timeout=2) as response:
            page = response.read()
            assert b"does not diagnose conditions" in page
            assert b"Setup dashboard" in page and b"Installation progress" in page
        setup = _request(url, "/api/setup/status")
        assert setup["ready_for_simulator"] is True
        assert _request(url, "/api/models")["models"]
        first = _request(url, "/api/models/status")
        second = _request(url, "/api/models/status")
        assert first == second and first["stage"] == "idle"
        result = _request(url, "/api/models/install", {"model_id": "mock-llm", "confirm": True})
        assert result["result"] == "Installation started"
        assert _request(url, "/api/models/status")["stage"] == "complete"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_voice_install_endpoint_uses_confirmed_manifest_request(tmp_path: Path):
    payload = b"local fixture"
    download_server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureDownloadHandler)
    _FixtureDownloadHandler.payload = payload
    download_thread = threading.Thread(target=download_server.serve_forever, daemon=True)
    download_thread.start()
    manifest = tmp_path / "voice.toml"
    manifest.write_text(
        f'''manifest_version = 1
[[models]]
id = "faster-whisper-small"
purpose = "stt"
provider = "faster-whisper"
source_url = "https://example.test/card"
license_url = "https://example.test/license"
recommended_storage = "fixture"
automatic_download_allowed = true
activation_allowed = true
[[models.files]]
name = "model.bin"
url = "http://127.0.0.1:{download_server.server_port}/model"
sha256 = "{hashlib.sha256(payload).hexdigest()}"
''',
        encoding="utf-8",
    )
    root = tmp_path / "data" / "models" / "voice"
    setup = VoiceModelSetup(
        tmp_path / "data",
        manifest_path=manifest,
        download_manager=DownloadManager(root, allow_http_for_tests=True),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(FakeApp(), voice_setup=setup))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        detail = _request(url, "/api/voice/status/stt")
        result = _request(
            url,
            "/api/voice/install/stt",
            {"model_id": detail["model_id"], "confirm": True},
        )
        assert result["operation"] == "download" and result["state"] == "downloading"
        for _ in range(50):
            if _request(url, "/api/voice/progress")["stage"] == "verified":
                break
            time.sleep(0.02)
        assert (setup.stt_path / "model.bin").read_bytes() == payload
        assert _request(url, "/api/voice/verify/stt", {})["verified"] is True
    finally:
        server.shutdown()
        download_server.shutdown()
        server.server_close()
        download_server.server_close()
        thread.join(timeout=2)
        download_thread.join(timeout=2)


class _FixtureDownloadHandler(BaseHTTPRequestHandler):
    payload = b""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, _format, *_args):
        return
