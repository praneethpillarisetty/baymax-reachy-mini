# Hardware readiness

Baymax defaults to `BAYMAX_MODE=simulator`, `BAYMAX_ROBOT_BACKEND=simulator`,
`BAYMAX_LLM_BACKEND=mock`, and `BAYMAX_VOICE_MODE=mock`. SDK import success alone never means
that physical support is ready. Run `baymax robot-status` for the side-effect-free capability report.

## 1. Offline CI-testable

- Simulator conversation, emergency model bypass, no emergency motion, expression allow-list, and
  safe-stop cancellation.
- Fake SDK connection/version/timeout, command limits, watchdog, cleanup, and safe-stop callbacks.
- Mock Ollama HTTP responses, bounded retry/failure behavior, model registry, activation, rollback,
  fake STT/TTS, cancellation, and temporary-file deletion.
- Configuration validation, redacted diagnostics, localhost UI setup/progress/error recovery, Linux
  ARM64 installation planning, and Windows packaging configuration inspection.

These tests do not import an optional SDK, contact Ollama, access an audio device, or connect to a
robot. Tests marked `physical` are automatically skipped unless `BAYMAX_PHYSICAL_TESTS=1`.

## 2. Local laptop-testable without Reachy

- A real Ollama installation/model on loopback, or on a private LAN only after
  `BAYMAX_ALLOW_OLLAMA_LAN=true`; firewall and routing must be reviewed separately.
- Explicit local STT/TTS executables, model files, microphone, speaker, latency, and cancellation.
- Windows wheel/executable/installer creation on Windows. The source configuration can be tested in
  CI, but a Windows artifact must be produced and launched on Windows.

## 3. Physical Reachy-required

- USB/local and network discovery, motors, official media devices, safe-stop behavior, watchdog
  timing, expression geometry, Raspberry Pi image compatibility, and official app deployment.
- Supervised smoke testing and every item in `physical-validation-checklist.md`.

## Official SDK verification blocker

The 2026-08-08 environment could not retrieve the official repository: Git HTTPS returned 403 and
the web service returned 401. Missing official information is: exact source commit/tag and supported
SDK version/distribution; constructor and local/network arguments; connection state/timeout API;
safe-stop registration and shutdown lifecycle; bounded head/antenna motion calls and limits; audio
and camera APIs; app template metadata; and setup/deploy/update/restart/log/rollback/shutdown
commands. `ReachySDKBoundary` is a Baymax-owned injection seam for deterministic fakes, **not** an
official API. Production remains locked until a reviewed wrapper supplies the verified contract.
