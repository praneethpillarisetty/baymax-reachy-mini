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

Configuration is read from `--config FILE` and then overridden by environment variables. Use `config/default.toml`, `config/laptop-ollama.toml`, or the deliberately hardware-locked `config/standalone.toml`. Non-loopback Ollama URLs require explicit `BAYMAX_ALLOW_OLLAMA_LAN=true`.

## Commands

* `baymax --once "hello"` / `baymax` — mock simulator conversation.
* `baymax doctor [--json]`, `baymax config show`, `baymax config validate` — actionable cross-platform diagnostics.
* `baymax data export --output data.json`, `baymax data delete --yes` — local-data controls.
* `baymax export --output profile.zip [--include-reminders]`, `baymax import --input profile.zip --settings-output imported.json` — checksummed versioned transfer with v1 migration.
* `baymax models list`, `baymax models inspect --profile PROFILE` — registry validation and LiteRT dry-run inspection.
* `baymax ui` — open a dependency-free local browser interface on `127.0.0.1`.
* `baymax robot-smoke --confirm-supervised` — deliberately fails closed until the official SDK adapter and hardware connection are validated.
* `baymax safe-stop` — stop the selected adapter safely.

## Verification boundary

On 2026-08-06, this environment attempted the requested official GitHub and Hugging Face sources before editing; the provided web service returned HTTP 401 and direct HTTPS returned 403. Consequently, the code does **not** fabricate a Reachy SDK version, distribution name, constructor, media API, simulator command, app entry point, or robot deployment command. Physical mode fails closed and `deploy/reachy-mini` awaits the current official generated template. See the [compatibility matrix](docs/development-setup.md) and [Reachy installation gate](docs/reachy-mini-installation.md).

Documentation: [architecture](docs/architecture.md), [development](docs/development-setup.md), [doctor](docs/doctor.md), [Windows](docs/windows-installation.md), [Ollama](docs/ollama-installation.md), [simulator](docs/simulator.md), [Reachy Mini](docs/reachy-mini-installation.md), [LiteRT](docs/litert-models.md), [profiles](docs/model-profiles.md), [voice](docs/voice.md), [transfer](docs/import-export.md), [packaging](docs/packaging.md), [safety](docs/healthcare-safety.md), [privacy](docs/privacy.md), [troubleshooting](docs/troubleshooting.md), and [physical checklist](docs/physical-robot-checklist.md).
