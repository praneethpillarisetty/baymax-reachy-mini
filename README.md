# Baymax-inspired Reachy Mini wellness companion

**Current status: Phase 7 — real local voice setup and Reachy Mini deployment preparation.**

| Capability | Laptop | Reachy Lite | Reachy Wireless |
|---|---|---|---|
| Text/Ollama | Adapter is mock-server tested; live Ollama unverified here | Laptop-hosted profile | Private-LAN hybrid is opt-in; CM4 4B model blocked |
| STT | faster-whisper-small installer; runtime required | Laptop-hosted | tiny candidate unsupported pending CM4 test |
| TTS | Lessac files installer; verified Piper runtime required | Laptop-hosted | ARM64 runtime unsupported pending CM4 test |
| Simulator | Available | Available before hardware | Available/fail-closed before hardware |
| Robot connection | No hardware needed | Official local/USB SDK validation pending | Official network SDK validation pending |
| Physical motion | Disabled by default | Supervised hardware test required | Supervised hardware test required |

A local-first, simulator-first wellness companion—not a medical device, clinician, diagnostic tool, or emergency service. What works without hardware: safety, text UI, simulator, mock audio, manifests, resumable download mechanics, and fake-server endpoint tests. Real microphones, speakers, Ollama, SDK connections, CM4 model performance, and all physical movement require the relevant local hardware and explicit validation.

## Start locally

```bash
python -m venv .venv
# Linux/macOS: . .venv/bin/activate    Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
baymax --once "hello"
baymax doctor
python -m pytest
```

Windows PowerShell uses `py -m venv .venv; .\.venv\Scripts\Activate.ps1; py -m pip install -e ".[test]"; py -m baymax.cli ui`. Linux/Raspberry Pi uses `python3 -m venv .venv && . .venv/bin/activate && python -m pip install -e '.[test]'`. Laptop setup comes first; do not deploy laptop-only models to a CM4.

## Voice setup order

1. Run `baymax ui`, open **STT**, review its source/license/size/destination confirmation, and choose **Install**.
2. Watch progress; after a failure use **Retry** (which resumes `.partial`) or **Cancel**. Choose **Verify**, then explicitly **Activate** only after installing `faster-whisper`.
3. Repeat for **TTS**. Both Lessac files are required. Install Piper separately from its trusted project/package, configure its path, and verify that its architecture matches the host before activation.
4. Test microphone and speaker. Mock mode visibly means no transcription or spoken audio.

Models are outside Git: `%LOCALAPPDATA%\BaymaxCompanion\models\voice\` on Windows and `~/.local/share/baymax-companion/models/voice/` on Linux. DownloadManager's hashed JSON records under `models/voice/.state/` are the single progress authority; inspect them through `baymax voice-model progress` or `/api/voice/debug` rather than editing them. States are `idle`, `downloading`, `paused`, `verifying`, `verified`, `failed`, and `cancelled`. To uninstall, stop Baymax and remove only the relevant directory below `models/voice`; never delete arbitrary paths. A failed checksum removes the unsafe partial; network interruption or cancellation preserves a safe `.partial` for Retry.

The Windows executable bundles the approved voice manifest. Python 3.11+ uses the standard-library `tomllib`; Python 3.10 uses the declared `tomli` compatibility dependency, allowing PyInstaller to discover either import statically.

Reachy Mini Lite is laptop-hosted and must use a verified official local/USB daemon flow. Reachy Mini Wireless is CM4-hosted and must use a verified official network flow; `reachy-mini.local` is only a discovery candidate, not robot identity proof. Until the SDK wrapper and real hardware pass supervised checks, use the simulator and run `baymax safe-stop`; no discovery/status command may move hardware.

Configuration is read from `--config FILE`, optional `.env`, and then environment variables. Use `config/default.toml`, `config/laptop-ollama.toml`, or the deliberately inference-locked `config/standalone.toml`. Non-loopback Ollama URLs require explicit `BAYMAX_ALLOW_OLLAMA_LAN=true`. See [runtime modes](docs/runtime-modes.md).

## Commands

* `baymax --once "hello"` / `baymax` — conversation with backend/fallback diagnostics; add
  `--json` to a one-shot request for machine-readable output.
* `baymax doctor [--json]`, `baymax config show`, `baymax config validate` — actionable cross-platform diagnostics.
* `baymax data export --output data.json`, `baymax data delete --yes` — local-data controls.
* `baymax export --output profile.zip [--include-reminders]`, `baymax import --input profile.zip --settings-output imported.json` — checksummed versioned transfer with v1 migration.
* `baymax models list`, `baymax models inspect --profile PROFILE` — registry validation and LiteRT dry-run inspection.
* `baymax models recommend`, `baymax models plan --target auto`, `baymax models install --target auto --dry-run` — capability-aware, confirmation-gated setup with no hidden downloads.
* `baymax models status`, `baymax models test mock-llm`, `baymax models activate --llm mock-llm --yes`, `baymax models rollback --yes` — persistent progress and transactional activation controls.
* `baymax benchmark MODEL --label NAME` — metadata-only artifact inventory; it never implies runtime support.
* `baymax ui` — open a dependency-free local browser interface on `127.0.0.1`.
* `baymax voice-test microphone|speaker|asr|tts` — CI-safe adapter preflight with no retained audio.
* `baymax robot-smoke --confirm-supervised` — deliberately fails closed until the official SDK adapter and hardware connection are validated.
* `baymax robot-status` — print connection, safe-stop, SDK-discovery and capability status without connecting.
* `baymax robot-doctor`, `baymax robot-safe-stop` — inspect the Reachy-only gates or engage the local fail-closed stop boundary.
* `baymax diagnostics export [--output FILE]` — export bounded status metadata without logs, audio, credentials, or personal data.
* `baymax safe-stop` — stop the selected adapter safely.

## Verification boundary

On 2026-08-08, this environment attempted the requested official GitHub and Hugging Face sources before editing; the provided web service returned HTTP 401 and direct HTTPS returned 403. Consequently, the code does **not** fabricate a Reachy SDK version, distribution name, constructor, media API, simulator command, app entry point, or robot deployment command. Physical mode fails closed and `deploy/reachy-mini` awaits the current official generated template. See the [compatibility matrix](docs/development-setup.md) and [Reachy installation gate](docs/reachy-mini-installation.md).

Documentation: [architecture](docs/architecture.md), [model setup](docs/model-setup.md), [runtime modes](docs/runtime-modes.md), [development](docs/development-setup.md), [doctor](docs/doctor.md), [Windows](docs/windows-installation.md), [Ollama](docs/ollama-installation.md), [simulator](docs/simulator.md), [Reachy Mini](docs/reachy-mini-installation.md), [LiteRT](docs/litert-models.md), [profiles](docs/model-profiles.md), [voice](docs/voice.md), [transfer](docs/import-export.md), [packaging](docs/packaging.md), [safety](docs/healthcare-safety.md), [privacy](docs/privacy.md), [troubleshooting](docs/troubleshooting.md), and [physical checklist](docs/physical-robot-checklist.md).

## Validation status

| Area | Status |
|---|---|
| Shared core, safety, SQLite, browser UI, mock audio | **Implemented; simulator-tested in CI** |
| Ollama HTTP adapter | **Implemented; mock-server-tested; live laptop unverified here** |
| Windows executable and installer | **Configured and CI-built; current workflow status must be checked on the PR** |
| LiteRT | **Profile/inspection implemented; exact inference runner disabled and unverified** |
| Reachy built-in adapter boundary | **Fail-closed; local simulator-tested** |
| Official Reachy simulator | **Unverified** |
| Physical Reachy Mini Wireless | **Not tested; all motion disabled** |
