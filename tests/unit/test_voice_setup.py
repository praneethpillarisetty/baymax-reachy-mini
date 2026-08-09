import hashlib
import json
from pathlib import Path
from urllib.error import URLError

import pytest

from baymax.voice.providers import MockSpeechRecognizer, MockSpeechSynthesizer
from baymax.voice.setup import VoiceModelSetup, provider_status


class Response:
    def __init__(self, payload: bytes, *, checksum: str | None = None):
        self.payload = payload
        self.position = 0
        self.status = 206
        self.headers = {
            "Content-Length": str(len(payload)),
            "X-Linked-Etag": checksum or hashlib.sha256(payload).hexdigest(),
        }

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, size=-1):
        if self.position:
            return b""
        self.position = len(self.payload)
        return self.payload


def test_no_voice_model_installed(tmp_path: Path):
    setup = VoiceModelSetup(tmp_path)
    assert not setup.stt_path.exists()
    assert setup.verify("stt") is False
    assert setup.progress()["stage"] == "failed"


def test_model_download_and_verification(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("baymax.voice.setup.STT_URLS", ("https://models.test/config.json",))
    setup = VoiceModelSetup(tmp_path, opener=lambda *_args, **_kwargs: Response(b"model"))
    setup.install("stt")
    assert (setup.stt_path / "config.json").read_bytes() == b"model"
    assert setup.verify("stt") is True


def test_download_resumes_partial_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("baymax.voice.setup.STT_URLS", ("https://models.test/model.bin",))
    setup = VoiceModelSetup(tmp_path, opener=lambda *_args, **_kwargs: Response(b"rest"))
    setup.stt_path.mkdir(parents=True)
    partial = setup.stt_path / "model.bin.partial"
    partial.write_bytes(b"start")
    checksum = hashlib.sha256(b"startrest").hexdigest()
    setup._open = lambda *_args, **_kwargs: Response(b"rest", checksum=checksum)
    setup.install("stt")
    assert (setup.stt_path / "model.bin").read_bytes() == b"startrest"


def test_checksum_failure_deletes_unsafe_partial(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("baymax.voice.setup.STT_URLS", ("https://models.test/model.bin",))
    setup = VoiceModelSetup(
        tmp_path,
        opener=lambda *_args, **_kwargs: Response(b"corrupt", checksum="0" * 64),
    )
    with pytest.raises(RuntimeError, match="Checksum verification failed"):
        setup.install("stt")
    assert not (setup.stt_path / "model.bin.partial").exists()


def test_free_space_and_network_failures_are_clear(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("baymax.voice.setup.STT_URLS", ("https://models.test/model.bin",))
    setup = VoiceModelSetup(
        tmp_path,
        opener=lambda *_args, **_kwargs: Response(b"model"),
        free_space=lambda _path: 0,
    )
    with pytest.raises(RuntimeError, match="Not enough free space"):
        setup.install("stt")
    setup = VoiceModelSetup(
        tmp_path, opener=lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline"))
    )
    with pytest.raises(URLError):
        setup.install("stt")
    assert setup.progress()["recovery"].startswith("Check the message")


def test_mock_providers_are_not_real_voice_available(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("baymax.voice.setup.device_status", lambda _kind: (True, "test device"))
    setup = VoiceModelSetup(tmp_path)
    asr = provider_status(MockSpeechRecognizer(), "stt", setup)
    tts = provider_status(MockSpeechSynthesizer(), "tts", setup)
    assert not asr.provider_selected and not asr.real_available
    assert not tts.provider_selected and not tts.real_available
    assert "real voice is disabled" in asr.detail


def test_activation_requires_verified_model_and_piper_runtime(tmp_path: Path):
    setup = VoiceModelSetup(tmp_path)
    with pytest.raises(RuntimeError, match="install and verify"):
        setup.activate("stt")
    setup.tts_path.parent.mkdir(parents=True)
    setup.tts_path.write_bytes(b"voice")
    checksum = hashlib.sha256(b"voice").hexdigest()
    (setup.tts_path.parent / ".baymax-verified.json").write_text(
        json.dumps({"files": {setup.tts_path.name: checksum}}), encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="Piper executable"):
        setup.activate("tts")
