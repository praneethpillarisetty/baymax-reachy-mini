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
from .models.manager import ModelManager

MAX_REQUEST_BYTES = 16_384
UI_HOST = "127.0.0.1"


@dataclass(frozen=True)
class UIContext:
    app: Any
    backend: str = "mock"
    mode: str = "simulator"
    voice: str = "mock"
    robot: str = "simulator"
    model_manager: ModelManager | None = None


def render_page(context: UIContext, response: str = "") -> bytes:
    reply = (
        f'<section class="reply"><strong>Companion</strong><p>{html.escape(response)}</p></section>'
        if response
        else ""
    )
    setup_html, models_html = "Simulator ready.", "No model registry loaded."
    progress_html, events_html = "No installation started.", "<li>No setup events.</li>"
    if context.model_manager:
        setup = context.model_manager.setup_status()
        caps = setup["capabilities"]
        setup_html = (
            f"<strong>Simulator ready · target {html.escape(str(setup['target']))}</strong><ul>"
            f"<li>{html.escape(str(caps['operating_system']))} / "
            f"{html.escape(str(caps['architecture']))} / Python {html.escape(str(caps['python_version']))}</li>"
            f"<li>RAM: {caps['ram_mb']} MB · Free disk: {caps['free_disk_mb']} MB</li>"
            f"<li>Microphone: {html.escape(str(caps['microphone']))} · Speaker: "
            f"{html.escape(str(caps['speaker']))}</li><li>Ollama: {caps['ollama_installed']} · "
            f"LiteRT: {caps['litert_runtime']} · Reachy SDK: {caps['reachy_sdk']}</li></ul>"
        )
        cards = []
        for card in context.model_manager.cards():
            identifier = html.escape(str(card["id"]), quote=True)
            reasons = html.escape("; ".join(str(item) for item in card["compatibility_reasons"]))
            action = "<strong>Automatic install blocked: unverified.</strong>"
            if card["status"] == "verified" or card["provider"] == "ollama":
                activation_note = (
                    "<p><strong>Activation remains blocked until this runtime contract is "
                    "verified.</strong></p>"
                    if card["status"] != "verified"
                    else ""
                )
                action = (
                    '<form method="post" action="/api/models/install">'
                    f'<input type="hidden" name="model_id" value="{identifier}">'
                    '<input type="hidden" name="confirm" value="yes">'
                    "<button onclick=\"return confirm('Install this model from its official source?')\">"
                    "Install</button></form>"
                    '<form method="post" action="/api/models/verify">'
                    f'<input type="hidden" name="model_id" value="{identifier}">'
                    "<button>Verify</button></form>"
                    '<form method="post" action="/api/models/test">'
                    f'<input type="hidden" name="model_id" value="{identifier}">'
                    "<button>Test</button></form>"
                    f"{activation_note}"
                )
            cards.append(
                f'<article class="card" data-category="{html.escape(str(card["purpose"]))}"><h3>{identifier}</h3><p>{card["purpose"]} via '
                f"{card['provider']} · {card['status']}</p><p>{card['download_size_mb']} MB · "
                f'{card["minimum_ram_mb"]} MB RAM</p><p>{reasons}</p><p><a rel="noreferrer" '
                f'href="{html.escape(str(card["source_url"]), quote=True)}">Official source</a> · '
                f'<a rel="noreferrer" href="{html.escape(str(card["license_url"]), quote=True)}">'
                f"License</a></p>{action}</article>"
            )
        models_html = "".join(cards)
        progress = context.model_manager.progress()
        percentage = progress["percentage"]
        label = "indeterminate" if percentage is None else f"{percentage:.1f}%"
        progress_html = (
            f"<p><strong>{progress['stage']}</strong> · {html.escape(str(progress['model_id'] or 'none'))}"
            f" · {label} · {progress['downloaded_bytes']} bytes</p>"
            f"<p>{html.escape(str(progress['error']))} {html.escape(str(progress['recovery']))}</p>"
            '<form method="post" action="/api/models/status">'
            '<button name="action" value="pause">Pause</button> '
            '<button name="action" value="resume">Resume</button> '
            '<button name="action" value="cancel">Cancel</button> '
            '<button name="action" value="retry">Retry</button></form>'
        )
        events_html = (
            "".join(
                f"<li><strong>{html.escape(event['level'])}</strong>: "
                f"{html.escape(event['message'])}</li>"
                for event in context.model_manager.events
            )
            or "<li>No setup events.</li>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Baymax Companion</title><style>
body{{font:16px system-ui,sans-serif;max-width:72rem;margin:2rem auto;padding:0 1rem;background:#f4f8fa;color:#17313b}}
main{{background:white;padding:2rem;border-radius:1.2rem;box-shadow:0 8px 30px #17313b20}}
textarea,input{{box-sizing:border-box;width:100%;padding:.7rem;font:inherit;margin:.3rem 0}}
textarea{{min-height:6rem}} button{{padding:.7rem 1.2rem;font:inherit;background:#19758b;color:white;border:0;border-radius:.6rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:1rem}} .card,.reply{{padding:1rem;background:#e9f6f8;border-radius:.8rem}}
small{{color:#334e57}} .warning{{border:.2rem solid #9c2f16;background:#fff1ed;padding:1rem}}
nav a{{display:inline-block;margin:.3rem 1rem .3rem 0}} code{{overflow-wrap:anywhere}}
</style></head><body><main><h1>Baymax Companion</h1>
<div class="warning" role="alert"><strong>Baymax Companion is a local wellness assistant.</strong><br>
It is not a medical device, does not diagnose conditions, and is not an emergency service.</div>
<nav aria-label="Setup sections"><a href="#companion">Companion</a><a href="#setup">Setup</a><a href="#models">Models</a><a href="#voice">Voice</a><a href="#robot">Robot</a><a href="#configuration">Configuration</a><a href="#diagnostics">Diagnostics</a></nav>
<section id="companion"><h2>Companion</h2>
<p><strong>Mode:</strong> {html.escape(context.mode)} · <strong>Model:</strong> {html.escape(context.backend)} · <strong>Voice:</strong> {html.escape(context.voice)} · <strong>Robot:</strong> {html.escape(context.robot)}</p>
<form method="post" action="/api/safe-stop"><button>Safe stop</button></form>
<form method="post" action="/api/message"><label for="message">How can I support you?</label>
<textarea id="message" name="message" required maxlength="4000"></textarea><button>Send</button></form>
{reply}</section><section id="setup"><h2>Setup dashboard</h2>{setup_html}<p><a href="/api/setup/status">Export setup status</a>. Simulator is the safe default.</p></section>
<section id="models"><h2>Models</h2><p><strong>Categories:</strong> LLM · STT · TTS · wake word</p><div class="grid">{models_html}</div><h3>Installation progress</h3>{progress_html}<p>State survives refresh. Unknown totals are shown as indeterminate.</p></section>
<section id="voice"><h2>Voice setup</h2><p>Microphone recording is off until explicitly tested. Temporary audio is deleted. Configure explicit local STT/TTS executables and models; no voice or actor is cloned.</p></section>
<section id="robot"><h2>Hardware readiness</h2><p><strong>Physical actions are disabled.</strong> A verified deployment would run one allow-listed, bounded head/antenna expression. Stop it with the Safe stop button or <code>baymax robot-safe-stop</code>; any failure must safe-stop and shut down.</p><ul><li>SDK/version: checked by <code>baymax robot-status</code>; unverified versions are rejected</li><li>Connection/motors/safe-stop: disconnected · movement disabled · registration required</li><li>Audio devices and STT/TTS: explicit local health checks required; temporary audio only</li><li>Model/Ollama: {html.escape(context.backend)} · private-LAN access requires explicit opt-in</li><li>Supervision/checklist: both explicit confirmations required</li><li>Limits: bounded timeout, watchdog, duration, and movement configuration</li></ul></section>
<section id="configuration"><h2>Configuration</h2><p>Active mode: {html.escape(context.mode)} · model provider: {html.escape(context.backend)} · voice: {html.escape(context.voice)} · robot: {html.escape(context.robot)}.</p><p>Use <code>baymax config show</code> for the redacted configuration. Model activation validates and tests every selection before applying it; rollback always requires confirmation.</p></section>
<h2>Wellness tools</h2><div class="grid">
<form class="card" method="post" action="/api/reminders"><strong>Reminder</strong><input name="title" placeholder="Title" required><input name="when" placeholder="When" required><button>Create</button></form>
<form class="card" method="post" action="/api/mood"><strong>Mood check-in</strong><input name="mood" placeholder="How do you feel?" required><button>Record</button></form>
<form class="card" method="post" action="/api/hydration"><strong>Hydration</strong><input name="milliliters" type="number" min="1" placeholder="Milliliters" required><button>Log</button></form>
</div><section id="diagnostics"><h2>Logs and diagnostics</h2><ul>{events_html}</ul><p><a href="/api/setup/events">Export setup events</a> · <a href="/api/health">System status</a> · <a href="/api/export">Export local data</a>. Diagnostics redact paths and secrets.</p></section><p><a href="/api/reminders">List reminders</a> · <a href="/api/wellness">Wellness summary</a></p>
</main></body></html>""".encode()


def create_handler(
    app: Any,
    *,
    backend: str = "mock",
    mode: str = "simulator",
    voice: str = "mock",
    robot: str = "simulator",
    model_manager: ModelManager | None = None,
) -> type[BaseHTTPRequestHandler]:
    context = UIContext(app, backend, mode, voice, robot, model_manager)

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
            elif path == "/api/models" and context.model_manager:
                self._json({"models": context.model_manager.cards()})
            elif path in {"/api/models/status", "/api/models/progress"} and context.model_manager:
                self._json(context.model_manager.progress())
            elif path == "/api/setup/status" and context.model_manager:
                self._json(context.model_manager.setup_status())
            elif path == "/api/setup/events" and context.model_manager:
                self._json({"events": context.model_manager.events})
            else:
                self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1:
                    raise ValueError("Request is empty")
                if length > MAX_REQUEST_BYTES:
                    self._json(
                        {"ok": False, "error": "Request exceeds the 16384-byte limit"},
                        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    )
                    return
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
                elif path == "/api/models/install" and context.model_manager:
                    identifier = values.get("model_id")
                    if not isinstance(identifier, str):
                        raise ValueError("model_id is required")
                    confirmed = values.get("confirm") in {True, "yes", "true"}
                    context.model_manager.start_install(identifier, confirmed=confirmed)
                    result = "Installation started"
                elif (
                    path
                    in {
                        "/api/models/status",
                        "/api/models/pause",
                        "/api/models/resume",
                        "/api/models/cancel",
                        "/api/models/retry",
                    }
                    and context.model_manager
                ):
                    action = (
                        path.rsplit("/", 1)[-1]
                        if path != "/api/models/status"
                        else values.get("action")
                    )
                    if not isinstance(action, str):
                        raise ValueError("action is required")
                    context.model_manager.control(action)
                    result = f"Installation {action} requested"
                elif path == "/api/models/verify" and context.model_manager:
                    identifier = values.get("model_id")
                    if not isinstance(identifier, str):
                        raise ValueError("model_id is required")
                    result = context.model_manager.verify(identifier)
                elif path == "/api/models/test" and context.model_manager:
                    identifier = values.get("model_id")
                    if not isinstance(identifier, str):
                        raise ValueError("model_id is required")
                    result = context.model_manager.test(identifier)
                elif path == "/api/models/activate" and context.model_manager:
                    if values.get("confirm") not in {True, "yes", "true"}:
                        raise ValueError("activation requires confirmation")
                    selected = {
                        role: value
                        for role in ("llm", "stt", "tts", "wake_word")
                        if isinstance((value := values.get(role, "")), str)
                    }
                    result = context.model_manager.activate(selected)
                elif path == "/api/models/rollback" and context.model_manager:
                    if values.get("confirm") not in {True, "yes", "true"}:
                        raise ValueError("rollback requires confirmation")
                    result = context.model_manager.rollback()
                elif path == "/api/reminders":
                    result = self._tool("create_reminder", values)
                elif path == "/api/mood":
                    result = self._tool("mood_check_in", values)
                elif path == "/api/hydration":
                    result = self._tool("log_hydration", values)
                else:
                    self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)
                    return
            except KeyError as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.NOT_FOUND)
                return
            except PermissionError as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.FORBIDDEN)
                return
            except FileNotFoundError as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.CONFLICT)
                return
            except RuntimeError as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.CONFLICT)
                return
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
                return
            if self.headers.get("Accept", "").startswith("application/json") or self.headers.get(
                "Content-Type", ""
            ).startswith("application/json"):
                self._json({"ok": True, "result": result})
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
    model_manager: ModelManager | None = None,
) -> None:
    server = ThreadingHTTPServer(
        (UI_HOST, port),
        create_handler(
            app,
            backend=backend,
            mode=mode,
            voice=voice,
            robot=robot,
            model_manager=model_manager,
        ),
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
