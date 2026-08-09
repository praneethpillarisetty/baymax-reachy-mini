# Baymax-inspired Reachy Mini wellness companion

A local-first, simulator-first wellness companion—not a medical device or clinician. Shared Python source supports a laptop/simulator target and a separately packaged Linux ARM64/Reachy target. The default path needs no robot, Ollama, model, microphone, speaker, or cloud service.

## Start locally

```bash
python -m venv .venv
# Linux/macOS: . .venv/bin/activate    Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
baymax --once "hello"
baymax doctor
python -m pytest
```

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
