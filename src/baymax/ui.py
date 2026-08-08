from __future__ import annotations

import html
import json
import tempfile
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .contracts import ActionRequest

MAX_REQUEST_BYTES = 16_384
UI_HOST = "127.0.0.1"


@dataclass(frozen=True)
class UIContext:
    app: Any
    backend: str = "mock"
    mode: str = "simulator"
    voice: str = "mock"
    robot: str = "simulator"


def render_page(context: UIContext, response: str = "") -> bytes:
    reply = (
        f'<section class="reply"><strong>Companion</strong><p>{html.escape(response)}</p></section>'
        if response
        else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Baymax Companion</title><style>
body{{font:16px system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;background:#f4f8fa;color:#17313b}}
main{{background:white;padding:2rem;border-radius:1.2rem;box-shadow:0 8px 30px #17313b20}}
textarea,input{{box-sizing:border-box;width:100%;padding:.7rem;font:inherit;margin:.3rem 0}}
textarea{{min-height:6rem}} button{{padding:.7rem 1.2rem;font:inherit;background:#19758b;color:white;border:0;border-radius:.6rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1rem}} .card,.reply{{padding:1rem;background:#e9f6f8;border-radius:.8rem}}
small{{color:#536d76}}
</style></head><body><main><h1>Baymax Companion</h1>
<p><small>Local wellness companion — not a medical device or emergency service.</small></p>
<p><strong>Mode:</strong> {html.escape(context.mode)} · <strong>Model:</strong> {html.escape(context.backend)} · <strong>Voice:</strong> {html.escape(context.voice)} · <strong>Robot:</strong> {html.escape(context.robot)}</p>
<form method="post" action="/api/safe-stop"><button>Safe stop</button></form>
<form method="post" action="/api/message"><label for="message">How can I support you?</label>
<textarea id="message" name="message" required maxlength="4000"></textarea><button>Send</button></form>
{reply}<h2>Wellness tools</h2><div class="grid">
<form class="card" method="post" action="/api/reminders"><strong>Reminder</strong><input name="title" placeholder="Title" required><input name="when" placeholder="When" required><button>Create</button></form>
<form class="card" method="post" action="/api/mood"><strong>Mood check-in</strong><input name="mood" placeholder="How do you feel?" required><button>Record</button></form>
<form class="card" method="post" action="/api/hydration"><strong>Hydration</strong><input name="milliliters" type="number" min="1" placeholder="Milliliters" required><button>Log</button></form>
</div><p><a href="/api/reminders">List reminders</a> · <a href="/api/wellness">Wellness summary</a> · <a href="/api/export">Export local data</a> · <a href="/api/health">System status</a></p>
</main></body></html>""".encode()


def create_handler(
    app: Any, *, backend: str = "mock", mode: str = "simulator", voice: str = "mock",
    robot: str = "simulator",
) -> type[BaseHTTPRequestHandler]:
    context = UIContext(app, backend, mode, voice, robot)

    class UIHandler(BaseHTTPRequestHandler):
        def _send(
            self,
            body: bytes,
            status: HTTPStatus = HTTPStatus.OK,
            content_type: str = "text/html; charset=utf-8",
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self._send(json.dumps(value).encode(), status, "application/json; charset=utf-8")

        def _tool(self, name: str, arguments: dict[str, Any]) -> str:
            return context.app.tools.execute(ActionRequest(name, arguments))

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                self._send(render_page(context))
            elif path == "/api/health":
                model = context.app.model
                model_ok, detail = (True, "built-in backend available")
                if hasattr(model, "health_check"):
                    model_ok, detail = model.health_check()
                self._json(
                    {
                        "status": "ok",
                        "backend": context.backend,
                        "mode": context.mode,
                        "model_available": model_ok,
                        "model_detail": detail,
                        "bind_host": UI_HOST,
                        "voice": context.voice,
                        "robot": context.app.robot.status(),
                    }
                )
            elif path == "/api/reminders":
                self._json({"result": self._tool("list_reminders", {})})
            elif path == "/api/wellness":
                self._json({"result": self._tool("wellness_summary", {})})
            elif path == "/api/export":
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / "baymax-data.json"
                    context.app.tools.store.export(output)
                    self._send(output.read_bytes(), content_type="application/json; charset=utf-8")
            else:
                self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > MAX_REQUEST_BYTES:
                    raise ValueError("Request is empty or too large")
                raw = self.rfile.read(length)
                if self.headers.get("Content-Type", "").startswith("application/json"):
                    values = json.loads(raw)
                    if not isinstance(values, dict):
                        raise ValueError("JSON body must be an object")
                else:
                    values = {
                        key: items[0]
                        for key, items in parse_qs(raw.decode(errors="replace")).items()
                    }
                path = urlparse(self.path).path
                if path in {"/", "/api/message"}:
                    message = values.get("message", "")
                    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
                        raise ValueError("Message is empty or too large")
                    result = context.app.handle(message.strip()).message
                elif path == "/api/safe-stop":
                    context.app.safe_stop()
                    result = "Safe stop engaged"
                elif path == "/api/reminders":
                    result = self._tool("create_reminder", values)
                elif path == "/api/mood":
                    result = self._tool("mood_check_in", values)
                elif path == "/api/hydration":
                    result = self._tool("log_hydration", values)
                else:
                    self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)
                    return
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            if self.headers.get("Accept", "").startswith("application/json") or self.headers.get(
                "Content-Type", ""
            ).startswith("application/json"):
                self._json({"result": result})
            else:
                self._send(render_page(context, result))

        def log_message(self, format: str, *args: object) -> None:
            return

    return UIHandler


def run_ui(
    app: Any,
    port: int = 8765,
    open_browser: bool = True,
    *,
    backend: str = "mock",
    mode: str = "simulator",
    voice: str = "mock",
    robot: str = "simulator",
) -> None:
    server = ThreadingHTTPServer(
        (UI_HOST, port), create_handler(app, backend=backend, mode=mode, voice=voice, robot=robot)
    )
    url = f"http://{UI_HOST}:{server.server_port}/"
    print(f"Baymax UI: {url} (press Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
