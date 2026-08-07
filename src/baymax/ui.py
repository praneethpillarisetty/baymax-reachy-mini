from __future__ import annotations

import html
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

MAX_REQUEST_BYTES = 16_384


def render_page(response: str = "") -> bytes:
    message = (
        f'<section class="reply"><strong>Companion</strong><p>{html.escape(response)}</p></section>'
        if response
        else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Baymax Companion</title><style>
body{{font:18px system-ui,sans-serif;max-width:44rem;margin:4rem auto;padding:0 1rem;background:#f4f8fa;color:#17313b}}
main{{background:white;padding:2rem;border-radius:1.2rem;box-shadow:0 8px 30px #17313b20}}
textarea{{box-sizing:border-box;width:100%;min-height:7rem;padding:.8rem;font:inherit}}
button{{margin-top:1rem;padding:.7rem 1.2rem;font:inherit;background:#19758b;color:white;border:0;border-radius:.6rem}}
.reply{{margin-top:1.5rem;padding:1rem;background:#e9f6f8;border-radius:.8rem}}
small{{color:#536d76}}
</style></head><body><main><h1>Baymax Companion</h1>
<p><small>Local wellness companion — not a medical device or emergency service.</small></p>
<form method="post"><label for="message">How can I support you?</label>
<textarea id="message" name="message" required maxlength="4000"></textarea><button>Send</button></form>
{message}</main></body></html>""".encode()


def create_handler(app: Any) -> type[BaseHTTPRequestHandler]:
    class UIHandler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path != "/":
                self._send(render_page("Page not found."), HTTPStatus.NOT_FOUND)
                return
            self._send(render_page())

        def do_POST(self) -> None:
            if self.path != "/":
                self._send(render_page("Page not found."), HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send(render_page("Invalid request."), HTTPStatus.BAD_REQUEST)
                return
            if length < 1 or length > MAX_REQUEST_BYTES:
                self._send(render_page("Message is empty or too large."), HTTPStatus.BAD_REQUEST)
                return
            values = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            text = values.get("message", [""])[0].strip()
            if not text or len(text) > 4000:
                self._send(render_page("Message is empty or too large."), HTTPStatus.BAD_REQUEST)
                return
            result = app.handle(text)
            self._send(render_page(result.message))

        def log_message(self, format: str, *args: object) -> None:
            return

    return UIHandler


def run_ui(app: Any, port: int = 8765, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), create_handler(app))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Baymax UI: {url} (press Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
