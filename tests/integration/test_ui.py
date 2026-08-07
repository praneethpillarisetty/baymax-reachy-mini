import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from baymax.contracts import ModelResponse
from baymax.ui import create_handler


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
