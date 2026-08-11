import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from baymax.voice.download import (
    DownloadError,
    DownloadManager,
    application_voice_dir,
    safe_filename,
)

PAYLOAD = b"fixture voice model"


class ModelServer(BaseHTTPRequestHandler):
    failures = 0

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/model")
            self.end_headers()
            return
        if self.path == "/retry" and type(self).failures < 1:
            type(self).failures += 1
            self.send_response(503)
            self.end_headers()
            return
        start = 0
        if value := self.headers.get("Range"):
            start = int(value.removeprefix("bytes=").removesuffix("-"))
        body = PAYLOAD[start:]
        self.send_response(206 if start else 200)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Linked-Etag", hashlib.sha256(PAYLOAD).hexdigest())
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


@pytest.fixture
def model_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), ModelServer)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def manager(tmp_path: Path) -> DownloadManager:
    return DownloadManager(tmp_path, allow_http_for_tests=True, sleep=lambda _seconds: None)


@pytest.mark.parametrize("endpoint", ["model", "redirect", "retry"])
def test_success_redirect_and_retry(tmp_path: Path, model_server: str, endpoint: str):
    target = tmp_path / "approved"
    manager(tmp_path).download(
        "fixture",
        (
            (
                "model.bin",
                f"{model_server}/{endpoint}",
                hashlib.sha256(PAYLOAD).hexdigest(),
                len(PAYLOAD),
            ),
        ),
        target,
    )
    assert (target / "model.bin").read_bytes() == PAYLOAD
    assert not (target / "model.bin.partial").exists()


def test_resume_range_and_persisted_progress(tmp_path: Path, model_server: str):
    target = tmp_path / "approved"
    target.mkdir()
    (target / "model.bin.partial").write_bytes(PAYLOAD[:7])
    download = manager(tmp_path)
    download.download(
        "fixture", (("model.bin", f"{model_server}/model", None, len(PAYLOAD)),), target
    )
    assert (target / "model.bin").read_bytes() == PAYLOAD
    assert download.progress("fixture").state == "verified"
    assert json.loads(next((tmp_path / ".state").iterdir()).read_text())["state"] == "verified"


def test_checksum_space_duplicate_and_safe_paths(tmp_path: Path, model_server: str):
    with pytest.raises(DownloadError, match="Not enough"):
        DownloadManager(tmp_path, allow_http_for_tests=True, free_space=lambda _path: 0).download(
            "space", (("model.bin", f"{model_server}/model", None, None),), tmp_path / "space"
        )
    with pytest.raises(DownloadError, match="Checksum"):
        manager(tmp_path).download(
            "checksum",
            (("model.bin", f"{model_server}/model", "0" * 64, None),),
            tmp_path / "checksum",
        )
    with pytest.raises(DownloadError):
        safe_filename("../escape")
    assert application_voice_dir("nt", {"LOCALAPPDATA": r"C:\Users\Test\AppData\Local"}).parts[
        -3:
    ] == (
        "BaymaxCompanion",
        "models",
        "voice",
    )
    assert application_voice_dir("posix", {"XDG_DATA_HOME": "/tmp/data"}) == Path(
        "/tmp/data/baymax-companion/models/voice"
    )
