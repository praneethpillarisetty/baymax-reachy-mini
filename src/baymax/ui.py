from __future__ import annotations

import html
import json
import tempfile
import time
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .contracts import ActionRequest
from .voice.providers import MockSpeechRecognizer, MockSpeechSynthesizer

MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_AUDIO_SECONDS = 30
UI_HOST = "127.0.0.1"


@dataclass(frozen=True)
class UIContext:
    app: Any
    backend: str = "mock"
    mode: str = "simulator"
    voice: str = "mock"
    robot: str = "simulator"
    model: str = "built-in"
    asr: Any = None
    tts: Any = None
    model_manager: Any = None


def render_page(context: UIContext, response: str = "") -> bytes:
    reply = f'<div class="assistant">{html.escape(response)}</div>' if response else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Baymax Companion</title>
<style>body{{font:16px system-ui;margin:auto;max-width:1100px;padding:20px;background:#eef6f8;color:#17313b}}.warning,.error{{border:2px solid #a33;padding:12px;background:#fff3ef}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}.card{{background:white;border-radius:14px;padding:18px;box-shadow:0 4px 18px #1232}}textarea{{width:100%;min-height:90px;box-sizing:border-box}}button{{padding:9px;margin:4px;background:#16748a;color:white;border:0;border-radius:7px}}button:disabled{{opacity:.5}}.badge{{background:#d9eef2;padding:4px 8px;border-radius:20px}}.message{{padding:10px;margin:8px 0;background:#edf7fa;border-radius:8px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}} </style></head><body>
<h1>Baymax Companion</h1><div class="warning"><b>Local wellness support only.</b> Baymax is not a medical device, does not diagnose conditions, and is not an emergency service. Call local emergency services in an emergency.</div>
<p><span class="badge">LLM: {html.escape(context.backend)}</span> <span class="badge">Model: {html.escape(context.model)}</span> <span class="badge">ASR: {html.escape(context.voice)}</span> <span class="badge">Robot: {html.escape(context.robot)}</span></p>
<div class="grid"><section class="card"><h2>Text Chat</h2><div id="history">{reply}</div><textarea id="message" maxlength="4000" placeholder="How can I support you?"></textarea><button id="send">Send</button><button id="test">Test Ollama</button><button id="retry" hidden>Retry</button><div id="error" class="error" hidden></div></section>
<section class="card"><h2>Voice Chat</h2><b id="voiceState">Ready</b><p id="timer">00:00</p><button id="record">Start recording</button><button id="stopRecord" disabled>Stop recording</button><button id="sendTranscript" disabled>Send transcript</button><p id="transcript">Transcript preview</p><label><input id="auto" type="checkbox"> Automatic playback</label><br><button id="play" disabled>Play response</button><button id="stopPlay">Stop playback</button><a id="download" hidden download="baymax-response.wav">Download generated WAV</a><div id="micError" class="error" hidden></div></section>
<section class="card"><h2>Diagnostics</h2><button id="refresh">Refresh status</button><button id="copy">Copy diagnostics</button><button id="export">Export diagnostics</button><pre id="diagnostics">Not loaded</pre></section>
<section class="card"><h2>Private local setup</h2><p>Audio is limited to 30 seconds/16 MiB, processed locally, and deleted after transcription. Chrome/Edge WebM/Opus is supported when the configured STT runtime has FFmpeg codecs.</p><code>BAYMAX_MODE=laptop<br>BAYMAX_LLM_BACKEND=ollama<br>OLLAMA_URL=http://127.0.0.1:11434<br>OLLAMA_MODEL=qwen3:4b</code></section></div>
<section hidden><h2>Setup dashboard</h2><h3>Installation progress</h3></section>
<script>
const $=id=>document.getElementById(id); let last='', transcript='', audioUrl='', recorder, chunks=[], started, tick;
function state(s){{$('voiceState').textContent=s}} function fail(e){{$('error').hidden=false;$('error').textContent=e;$('retry').hidden=false;state('Error')}}
async function send(text){{last=text;$('send').disabled=true;$('send').textContent='Sending…';$('error').hidden=true;state('Sending to Ollama');$('history').insertAdjacentHTML('beforeend',`<div class="message"><b>You</b><br>${{text.replace(/[&<>]/g,x=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[x]))}}</div>`);try{{let r=await fetch('/api/message',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:text}})}});let j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${{r.status}}`);$('history').insertAdjacentHTML('beforeend',`<div class="message"><b>Baymax (${{j.backend}})</b><br>${{j.message}}</div>`);$('diagnostics').textContent=JSON.stringify(j,null,2);state('Complete');$('play').disabled=false;if($('auto').checked)await speech(j.message)}}catch(e){{fail(e.message)}}finally{{$('send').disabled=false;$('send').textContent='Send'}}}}
$('send').onclick=()=>send($('message').value.trim());$('message').onkeydown=e=>{{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();$('send').click()}}}};$('retry').onclick=()=>send(last);$('test').onclick=()=>send('Reply with exactly: BAYMAX_UI_OLLAMA_TEST');
$('refresh').onclick=async()=>{{let r=await fetch('/api/health');$('diagnostics').textContent=JSON.stringify(await r.json(),null,2)}};$('copy').onclick=()=>navigator.clipboard.writeText($('diagnostics').textContent);$('export').onclick=()=>{{let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([$('diagnostics').textContent],{{type:'application/json'}}));a.download='baymax-diagnostics.json';a.click()}};
$('record').onclick=async()=>{{try{{if(!window.MediaRecorder)throw Error('This browser does not support MediaRecorder');let stream=await navigator.mediaDevices.getUserMedia({{audio:true}});chunks=[];recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>chunks.push(e.data);recorder.start();started=Date.now();state('Recording');$('record').disabled=true;$('stopRecord').disabled=false;tick=setInterval(()=>{{$('timer').textContent=new Date(Date.now()-started).toISOString().slice(14,19);if(Date.now()-started>30000)$('stopRecord').click()}},250)}}catch(e){{$('micError').hidden=false;$('micError').textContent=e.message;state('Error')}}}};
$('stopRecord').onclick=()=>{{clearInterval(tick);recorder.onstop=async()=>{{recorder.stream.getTracks().forEach(t=>t.stop());let blob=new Blob(chunks,{{type:recorder.mimeType}});if(blob.size>16777216){{fail('Recording exceeds 16 MiB');return}}state('Transcribing');try{{let r=await fetch('/api/transcribe',{{method:'POST',headers:{{'Content-Type':blob.type}},body:blob}});let j=await r.json();if(!r.ok)throw Error(j.error);transcript=j.transcript;$('transcript').textContent=transcript;$('sendTranscript').disabled=false;state('Ready')}}catch(e){{fail(e.message)}}}};recorder.stop();$('record').disabled=false;$('stopRecord').disabled=true}};$('sendTranscript').onclick=()=>send(transcript);
async function speech(text){{state('Generating speech');let r=await fetch('/api/speech',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{text}})}});if(!r.ok){{let j=await r.json();throw Error(j.error)}}let b=await r.blob();if(audioUrl)URL.revokeObjectURL(audioUrl);audioUrl=URL.createObjectURL(b);$('download').href=audioUrl;$('download').hidden=false;window.player=new Audio(audioUrl);window.player.onplay=()=>state('Playing');window.player.onended=()=>state('Complete');await window.player.play()}};$('play').onclick=()=>speech(document.querySelector('#history .message:last-child')?.innerText||'');$('stopPlay').onclick=()=>window.player?.pause();$('refresh').click();
</script></body></html>""".encode()


def create_handler(
    app: Any,
    *,
    backend="mock",
    mode="simulator",
    voice="mock",
    robot="simulator",
    model="built-in",
    recognizer=None,
    synthesizer=None,
    model_manager=None,
):
    context = UIContext(
        app,
        backend,
        mode,
        voice,
        robot,
        model,
        recognizer or MockSpeechRecognizer(),
        synthesizer or MockSpeechSynthesizer(),
        model_manager,
    )

    class UIHandler(BaseHTTPRequestHandler):
        def _send(self, body, status=HTTPStatus.OK, content_type="text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, value, status=HTTPStatus.OK):
            self._send(json.dumps(value).encode(), status, "application/json; charset=utf-8")

        def _tool(self, name, arguments):
            return context.app.tools.execute(ActionRequest(name, arguments))

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send(render_page(context))
            elif path == "/api/health":
                model_obj = context.app.model
                ok, detail = (
                    model_obj.health_check()
                    if hasattr(model_obj, "health_check")
                    else (True, "built-in backend available")
                )
                aok, adetail = context.asr.health_check()
                tok, tdetail = context.tts.health_check()
                self._json(
                    {
                        "status": "ok" if ok else "degraded",
                        "ollama_reachable": ok if context.backend == "ollama" else None,
                        "configured_model": context.model,
                        "active_llm_backend": context.backend,
                        "model_detail": detail,
                        "model_available": ok,
                        "asr_backend": context.asr.provider_name(),
                        "asr_available": aok,
                        "asr_detail": adetail,
                        "tts_backend": context.tts.provider_name(),
                        "tts_available": tok,
                        "tts_detail": tdetail,
                        "bind_host": UI_HOST,
                        "backend": context.backend,
                        "mode": context.mode,
                        "voice": context.voice,
                        "robot": context.app.robot.status(),
                    }
                )
            elif path == "/api/reminders":
                self._json({"result": self._tool("list_reminders", {})})
            elif path == "/api/wellness":
                self._json({"result": self._tool("wellness_summary", {})})
            elif path in {"/api/models/status", "/api/models/progress"} and context.model_manager:
                self._json(context.model_manager.progress())
            elif path == "/api/models" and context.model_manager:
                self._json({"models": context.model_manager.cards()})
            elif path == "/api/setup/status" and context.model_manager:
                self._json(context.model_manager.setup_status())
            else:
                self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1:
                    raise ValueError("Request is empty")
                if length > MAX_REQUEST_BYTES:
                    self._json(
                        {"ok": False, "error": "Request exceeds the 16 MiB limit"},
                        HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    )
                    return
                raw = self.rfile.read(length)
                path = urlparse(self.path).path
                if path == "/api/transcribe":
                    content = self.headers.get("Content-Type", "").split(";", 1)[0]
                    suffix = {
                        "audio/webm": ".webm",
                        "audio/ogg": ".ogg",
                        "audio/wav": ".wav",
                        "audio/x-wav": ".wav",
                    }.get(content)
                    if suffix is None:
                        raise ValueError(
                            f"Unsupported audio format: {content or 'missing Content-Type'}"
                        )
                    with tempfile.TemporaryDirectory(prefix="baymax-browser-audio-") as directory:
                        audio = Path(directory) / ("recording" + suffix)
                        audio.write_bytes(raw)
                        transcript = context.asr.transcribe(audio)
                    self._json(
                        {
                            "ok": True,
                            "transcript": transcript,
                            "provider": context.asr.provider_name(),
                        }
                    )
                    return
                values = (
                    json.loads(raw)
                    if self.headers.get("Content-Type", "").startswith("application/json")
                    else {k: v[0] for k, v in parse_qs(raw.decode(errors="replace")).items()}
                )
                if path in {"/", "/api/message"}:
                    message = values.get("message", "")
                    if not isinstance(message, str) or not message.strip() or len(message) > 4000:
                        raise ValueError("Message is empty or too large")
                    started = time.monotonic()
                    response = context.app.handle(message.strip())
                    if (
                        response.fallback_reason is not None
                        and response.backend == context.backend
                        and response.message.startswith("I am having trouble")
                    ):
                        raise RuntimeError(response.fallback_reason)
                    duration = round((time.monotonic() - started) * 1000, 2)
                    payload = {
                        "ok": True,
                        "result": response.message,
                        "message": response.message,
                        "emotion": response.emotion,
                        "actions": [
                            {"tool": a.tool, "arguments": a.arguments} for a in response.actions
                        ],
                        "backend": response.backend,
                        "model": context.model,
                        "fallback_used": response.fallback_reason is not None,
                        "fallback_reason": response.fallback_reason,
                        "request_duration_ms": duration,
                        "safety_status": "intervened" if response.backend == "safety" else "passed",
                    }
                    if self.headers.get("Content-Type", "").startswith("application/json"):
                        self._json(payload)
                    else:
                        self._send(render_page(context, response.message))
                    return
                if path == "/api/speech":
                    text = values.get("text", "")
                    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                        raise ValueError("Speech text is empty or too large")
                    with tempfile.TemporaryDirectory(prefix="baymax-browser-speech-") as directory:
                        output = Path(directory) / "response.wav"
                        context.tts.synthesize(text, output)
                        data = output.read_bytes()
                    self._send(data, content_type="audio/wav")
                    return
                if path == "/api/safe-stop":
                    context.app.safe_stop()
                    result = "Safe stop engaged"
                elif path == "/api/reminders":
                    result = self._tool("create_reminder", values)
                elif path == "/api/mood":
                    result = self._tool("mood_check_in", values)
                elif path == "/api/hydration":
                    result = self._tool("log_hydration", values)
                elif path == "/api/models/install" and context.model_manager:
                    context.model_manager.start_install(
                        str(values.get("model_id")),
                        confirmed=values.get("confirm") in {True, "yes"},
                    )
                    result = "Installation started"
                else:
                    self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)
                    return
                self._json({"ok": True, "result": result}) if self.headers.get(
                    "Content-Type", ""
                ).startswith("application/json") else self._send(render_page(context, result))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json(
                    {
                        "ok": False,
                        "error": str(exc),
                        "backend": context.backend,
                        "fallback_reason": None,
                    },
                    HTTPStatus.BAD_REQUEST,
                )
            except Exception as exc:  # noqa: BLE001 -- final HTTP boundary returns adapter failures
                self._json(
                    {
                        "ok": False,
                        "error": str(exc),
                        "backend": context.backend,
                        "fallback_reason": str(exc),
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )

        def log_message(self, format, *args):
            return

    return UIHandler


def run_ui(app, port=8765, open_browser=True, **kwargs):
    server = ThreadingHTTPServer((UI_HOST, port), create_handler(app, **kwargs))
    url = f"http://{UI_HOST}:{server.server_port}/"
    print(f"Baymax Companion UI: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
