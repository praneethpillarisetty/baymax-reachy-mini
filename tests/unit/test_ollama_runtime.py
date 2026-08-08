import io
import json
from pathlib import Path
from unittest.mock import patch

from baymax.models.ollama import OllamaConnectionError, OllamaModel


class Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def adapter() -> OllamaModel:
    return OllamaModel("http://127.0.0.1:11434", "local:1b", 0.1, 32, 0, retries=0)


def test_malformed_json_is_actionable():
    with patch("urllib.request.urlopen", return_value=Response(b"not-json")):
        try:
            adapter().installed_models()
        except OllamaConnectionError as exc:
            assert "malformed JSON" in str(exc)
        else:
            raise AssertionError("malformed JSON accepted")


def test_timeout_is_actionable():
    with patch("urllib.request.urlopen", side_effect=TimeoutError()):
        available, detail = adapter().health_check()
    assert not available
    assert "timed out" in detail


def test_verified_model_is_stored_atomically(tmp_path: Path):
    model = adapter()
    with patch.object(
        model,
        "_request",
        side_effect=[
            {"models": [{"name": "local:1b"}]},
            {"message": {"content": "ready"}},
        ],
    ):
        destination = tmp_path / "active.json"
        model.verify_and_store(destination)
    assert json.loads(destination.read_text()) == {
        "url": "http://127.0.0.1:11434",
        "model": "local:1b",
    }
