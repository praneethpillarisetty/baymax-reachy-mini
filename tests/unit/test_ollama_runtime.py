import io
import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

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


def test_private_lan_failure_reconnects_with_bounded_retry():
    model = OllamaModel("http://192.168.1.20:11434", "local:1b", 0.1, 32, 0, retries=1)
    with (
        patch(
            "urllib.request.urlopen", side_effect=[URLError("offline"), Response(b'{"models": []}')]
        ) as opened,
        patch("time.sleep") as slept,
    ):
        assert model.installed_models() == ()
    assert opened.call_count == 2
    slept.assert_called_once_with(0.1)


def test_safe_stop_cancels_ollama_before_request():
    model = adapter()
    model.cancel()
    with patch("urllib.request.urlopen") as opened:
        try:
            model.installed_models()
        except OllamaConnectionError as exc:
            assert "cancelled" in str(exc)
        else:
            raise AssertionError("cancelled request was sent")
    opened.assert_not_called()
