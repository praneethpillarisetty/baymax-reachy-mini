# Doctor command

Run `baymax doctor` or `baymax doctor --json`. It reports Python support, OS, CPU architecture, installed project/tool versions, writable database, selected audio backends, built-in simulator, Ollama executable and `/api/tags` reachability/configured model, LiteRT runtime/profile/artifacts, Reachy SDK import availability, and physical validation status. Each warning/failure has an action.

Optional missing services are warnings in mock mode. A selected backend missing its service/runtime/profile is a failure. Reachy SDK discovery is never reported as physical support: physical support remains failed/warned until a verified connection and supervised smoke test exist. On this source container Python 3.14 is intentionally reported unsupported; use Python 3.10–3.13.
