from __future__ import annotations

import html
import json
import tempfile
import threading
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
from .voice.setup import VoiceModelSetup, provider_status

MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_AUDIO_SECONDS = 30
UI_HOST = "127.0.0.1"


def _background_install(setup: VoiceModelSetup, component: str) -> None:
    try:
        setup.install(component)
    except Exception:  # noqa: BLE001 -- failure details are persisted for progress polling
        return


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
    voice_setup: VoiceModelSetup | None = None


def render_page(context: UIContext, response: str = "") -> bytes:
    reply = f'<div class="assistant">{html.escape(response)}</div>' if response else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Baymax Companion</title>
<style>body{{font:16px system-ui;margin:auto;max-width:1100px;padding:20px;background:#eef6f8;color:#17313b}}.warning,.error{{border:2px solid #a33;padding:12px;background:#fff3ef}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}.card{{background:white;border-radius:14px;padding:18px;box-shadow:0 4px 18px #1232}}textarea{{width:100%;min-height:90px;box-sizing:border-box}}button{{padding:9px;margin:4px;background:#16748a;color:white;border:0;border-radius:7px}}button:disabled{{opacity:.5}}.badge{{background:#d9eef2;padding:4px 8px;border-radius:20px}}.message{{padding:10px;margin:8px 0;background:#edf7fa;border-radius:8px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}} </style></head><body>
<h1>Baymax Companion</h1><div class="warning"><b>Local wellness support only.</b> Baymax is not a medical device, does not diagnose conditions, and is not an emergency service. Call local emergency services in an emergency.</div>
<p><span class="badge">LLM: {html.escape(context.backend)}</span> <span class="badge">Model: {html.escape(context.model)}</span> <span class="badge">ASR: {html.escape(context.voice)}</span> <span class="badge">Robot: {html.escape(context.robot)}</span></p>
<div id="voiceWarning" class="warning" hidden><b>Real voice models are not installed.</b> Mock/console providers are configured but real voice is disabled.</div>
<div class="grid"><section class="card"><h2>Text Chat</h2><div id="history">{reply}</div><textarea id="message" maxlength="4000" placeholder="How can I support you?"></textarea><button id="send">Send</button><button id="test">Test Ollama</button><button id="retry" hidden>Retry</button><div id="error" class="error" hidden></div></section>
<section class="card"><h2>Voice Chat</h2><b id="voiceState">Ready</b><p id="timer">00:00</p><button id="record">Start recording</button><button id="stopRecord" disabled>Stop recording</button><button id="sendTranscript" disabled>Send transcript</button><p id="transcript">Transcript preview</p><label><input id="auto" type="checkbox"> Automatic playback</label><br><button id="play" disabled>Play response</button><button id="stopPlay">Stop playback</button><a id="download" hidden download="baymax-response.wav">Download generated WAV</a><div id="micError" class="error" hidden></div></section>
<section class="card"><h2>Diagnostics</h2><button id="refresh">Refresh status</button><button id="copy">Copy diagnostics</button><button id="export">Export diagnostics</button><pre id="diagnostics">Not loaded</pre></section>
<section class="card"><h2>Local voice setup</h2><p>Defaults: <b>faster-whisper-small</b> and <b>Piper en_US-lessac-medium</b>. Downloads stay in the application data directory. Installation never activates a provider.</p><button data-action="install/stt">Install STT model</button><button data-action="install/tts">Install TTS model</button><button data-action="verify/stt">Verify STT</button><button data-action="verify/tts">Verify TTS</button><button id="testMic">Test microphone</button><button id="testSpeaker">Test speaker</button><button data-action="loop">Test complete voice loop</button><button data-action="cancel">Cancel download</button><button data-action="retry">Retry</button><pre id="voiceProgress">Idle</pre><label>STT model path <input id="sttPath"></label><br><label>Piper executable path <input id="piperExe"></label><br><label>Piper model path <input id="piperModel"></label><br><button id="saveVoice">Save paths</button><button data-action="activate/stt">Activate STT</button><button data-action="activate/tts">Activate TTS</button><div id="setupError" class="error" hidden></div></section>
<section class="card"><h2>Private local setup</h2><p>Audio is limited to 30 seconds/16 MiB, processed locally, and deleted after transcription. Chrome/Edge WebM/Opus is supported when the configured STT runtime has FFmpeg codecs.</p><code>BAYMAX_MODE=laptop<br>BAYMAX_LLM_BACKEND=ollama<br>OLLAMA_URL=http://127.0.0.1:11434<br>OLLAMA_MODEL=qwen3:4b</code></section></div>
<section hidden><h2>Setup dashboard</h2><h3>Installation progress</h3></section>
<script>
const $=id=>document.getElementById(id); let last='', transcript='', audioUrl='', recorder, chunks=[], started, tick;
function state(s){{$('voiceState').textContent=s}} function fail(e){{$('error').hidden=false;$('error').textContent=e;$('retry').hidden=false;state('Error')}}
async function send(text){{last=text;$('send').disabled=true;$('send').textContent='Sending…';$('error').hidden=true;state('Sending to Ollama');$('history').insertAdjacentHTML('beforeend',`<div class="message"><b>You</b><br>${{text.replace(/[&<>]/g,x=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[x]))}}</div>`);try{{let r=await fetch('/api/message',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:text}})}});let j=await r.json();if(!r.ok)throw Error(j.error||`HTTP ${{r.status}}`);$('history').insertAdjacentHTML('beforeend',`<div class="message"><b>Baymax (${{j.backend}})</b><br>${{j.message}}</div>`);$('diagnostics').textContent=JSON.stringify(j,null,2);state('Complete');$('play').disabled=false;if($('auto').checked)await speech(j.message)}}catch(e){{fail(e.message)}}finally{{$('send').disabled=false;$('send').textContent='Send'}}}}
$('send').onclick=()=>send($('message').value.trim());$('message').onkeydown=e=>{{if(e.key==='Enter'&&!e.shiftKey){{e.preventDefault();$('send').click()}}}};$('retry').onclick=()=>send(last);$('test').onclick=()=>send('Reply with exactly: BAYMAX_UI_OLLAMA_TEST');
$('refresh').onclick=async()=>{{let r=await fetch('/api/health'),j=await r.json();$('diagnostics').textContent=JSON.stringify(j,null,2);$('voiceWarning').hidden=!['mock'].includes(j.asr_backend)&&!['console','mock'].includes(j.tts_backend)}};$('copy').onclick=()=>navigator.clipboard.writeText($('diagnostics').textContent);$('export').onclick=()=>{{let a=document.createElement('a');a.href=URL.createObjectURL(new Blob([$('diagnostics').textContent],{{type:'application/json'}}));a.download='baymax-diagnostics.json';a.click()}};
$('record').onclick=async()=>{{try{{if(!window.MediaRecorder)throw Error('This browser does not support MediaRecorder');let stream=await navigator.mediaDevices.getUserMedia({{audio:true}});chunks=[];recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>chunks.push(e.data);recorder.start();started=Date.now();state('Recording');$('record').disabled=true;$('stopRecord').disabled=false;tick=setInterval(()=>{{$('timer').textContent=new Date(Date.now()-started).toISOString().slice(14,19);if(Date.now()-started>30000)$('stopRecord').click()}},250)}}catch(e){{$('micError').hidden=false;$('micError').textContent=e.message;state('Error')}}}};
$('stopRecord').onclick=()=>{{clearInterval(tick);recorder.onstop=async()=>{{recorder.stream.getTracks().forEach(t=>t.stop());let blob=new Blob(chunks,{{type:recorder.mimeType}});if(blob.size>16777216){{fail('Recording exceeds 16 MiB');return}}state('Transcribing');try{{let r=await fetch('/api/transcribe',{{method:'POST',headers:{{'Content-Type':blob.type}},body:blob}});let j=await r.json();if(!r.ok)throw Error(j.error);transcript=j.transcript;$('transcript').textContent=transcript;$('sendTranscript').disabled=false;state('Ready')}}catch(e){{fail(e.message)}}}};recorder.stop();$('record').disabled=false;$('stopRecord').disabled=true}};$('sendTranscript').onclick=()=>send(transcript);
async function speech(text){{state('Generating speech');let r=await fetch('/api/speech',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{text}})}});if(!r.ok){{let j=await r.json();throw Error(j.error)}}let b=await r.blob();if(audioUrl)URL.revokeObjectURL(audioUrl);audioUrl=URL.createObjectURL(b);$('download').href=audioUrl;$('download').hidden=false;window.player=new Audio(audioUrl);window.player.onplay=()=>state('Playing');window.player.onended=()=>state('Complete');await window.player.play()}};$('play').onclick=()=>speech(document.querySelector('#history .message:last-child')?.innerText||'');$('stopPlay').onclick=()=>window.player?.pause();$('refresh').click();
async function setupAction(action,payload={{}}){{$('setupError').hidden=true;try{{let r=await fetch('/api/voice/'+action,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}}),j=await r.json();if(!r.ok)throw Error(j.error);$('voiceProgress').textContent=JSON.stringify(j,null,2);await $('refresh').onclick()}}catch(e){{$('setupError').hidden=false;$('setupError').textContent=e.message}}}}document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>setupAction(b.dataset.action));
$('saveVoice').onclick=()=>setupAction('config',{{stt_model_path:$('sttPath').value,piper_executable_path:$('piperExe').value,piper_model_path:$('piperModel').value}});fetch('/api/voice/config').then(r=>r.json()).then(j=>{{$('sttPath').value=j.asr_model_path;$('piperExe').value=j.tts_executable;$('piperModel').value=j.tts_model_path}});setInterval(async()=>{{let r=await fetch('/api/voice/progress');$('voiceProgress').textContent=JSON.stringify(await r.json(),null,2)}},1000);
$('testMic').onclick=async()=>{{try{{let s=await navigator.mediaDevices.getUserMedia({{audio:true}}),d=await navigator.mediaDevices.enumerateDevices();s.getTracks().forEach(t=>t.stop());$('voiceProgress').textContent=`Microphone permission granted; ${{d.filter(x=>x.kind==='audioinput').length}} input(s)`}}catch(e){{$('setupError').hidden=false;$('setupError').textContent='Microphone test failed: '+e.message}}}};$('testSpeaker').onclick=()=>{{let c=new AudioContext(),o=c.createOscillator();o.connect(c.destination);o.start();o.stop(c.currentTime+.25);$('voiceProgress').textContent='Speaker test tone played'}};$('refresh').click();
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
    voice_setup=None,
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
        voice_setup or VoiceModelSetup(),
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
                ast = provider_status(context.asr, "stt", context.voice_setup)
                tst = provider_status(context.tts, "tts", context.voice_setup)
                self._json(
                    {
                        "status": "ok" if ok else "degraded",
                        "ollama_reachable": ok if context.backend == "ollama" else None,
                        "configured_model": context.model,
                        "active_llm_backend": context.backend,
                        "model_detail": detail,
                        "model_available": ok,
                        "asr_backend": context.asr.provider_name(),
                        "asr_available": ast.real_available,
                        "asr_detail": ast.detail
                        if ast.provider_selected
                        else "configured but real voice is disabled",
                        "asr_provider_selected": ast.provider_selected,
                        "asr_runtime_available": ast.runtime_available,
                        "asr_model_installed": ast.model_installed,
                        "asr_model_verified": ast.model_verified,
                        "microphone_available": ast.device_available,
                        "tts_backend": context.tts.provider_name(),
                        "tts_available": tst.real_available,
                        "tts_detail": tst.detail
                        if tst.provider_selected
                        else "configured but real voice is disabled",
                        "tts_provider_selected": tst.provider_selected,
                        "tts_runtime_available": tst.runtime_available,
                        "tts_model_installed": tst.model_installed,
                        "tts_model_verified": tst.model_verified,
                        "speaker_available": tst.device_available,
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
            elif path == "/api/voice/progress":
                self._json(context.voice_setup.progress())
            elif path == "/api/voice/config":
                self._json(context.voice_setup.config())
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
                if path.startswith("/api/voice/"):
                    action = path.removeprefix("/api/voice/")
                    if action in {"install/stt", "install/tts"}:
                        component = action.rsplit("/", 1)[1]
                        threading.Thread(
                            target=_background_install,
                            args=(context.voice_setup, component),
                            daemon=True,
                        ).start()
                        self._json({"ok": True, "result": "Download started"})
                    elif action in {"verify/stt", "verify/tts"}:
                        component = action.rsplit("/", 1)[1]
                        valid = context.voice_setup.verify(component)
                        self._json(
                            {"ok": valid, "verified": valid},
                            HTTPStatus.OK if valid else HTTPStatus.BAD_REQUEST,
                        )
                    elif action in {"activate/stt", "activate/tts"}:
                        component = action.rsplit("/", 1)[1]
                        self._json(
                            {
                                "ok": True,
                                "environment": context.voice_setup.activate(component),
                                "restart_required": True,
                            }
                        )
                    elif action == "config":
                        context.voice_setup.save_config(
                            str(values.get("stt_model_path", "")),
                            str(values.get("piper_executable_path", "")),
                            str(values.get("piper_model_path", "")),
                        )
                        self._json({"ok": True, **context.voice_setup.config()})
                    elif action == "cancel":
                        context.voice_setup.cancel()
                        self._json({"ok": True, "result": "Cancellation requested"})
                    elif action == "retry":
                        progress = context.voice_setup.progress()
                        component = str(progress.get("component", ""))
                        if component not in {"stt", "tts"}:
                            raise ValueError("Nothing to retry")
                        threading.Thread(
                            target=_background_install,
                            args=(context.voice_setup, component),
                            daemon=True,
                        ).start()
                        self._json({"ok": True, "result": "Retry started"})
                    elif action == "loop":
                        if (
                            context.asr.provider_name() == "mock"
                            or context.tts.provider_name() == "console"
                        ):
                            raise RuntimeError(
                                "Complete voice loop requires verified, active real STT and TTS providers"
                            )
                        self._json(
                            {
                                "ok": True,
                                "result": "Use Start recording, then Send transcript with automatic playback enabled",
                            }
                        )
                    else:
                        self._json({"error": "Page not found"}, HTTPStatus.NOT_FOUND)
                    return
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
