# Development setup and compatibility

| Component | Declared/test status | Notes |
|---|---|---|
| Shared core | Python 3.10–3.13 | CI matrix: Windows and Linux; no optional runtime imports. |
| Current container | Python 3.14.4 | Tests run, but packaging intentionally rejects 3.14. |
| Windows laptop | Source/CI target | PyInstaller and Inno Setup recipes supplied; installer build requires Windows. |
| Linux ARM64 | Source target | Architecture preflight supplied; actual robot image untested. |
| Reachy Mini SDK/app | Blocked | Exact current SDK/Python/app rules must be copied from official sources before enabling. |
| Ollama | HTTP adapter tested with mocks | Actual service/model not present in CI. |
| LiteRT | Profile contract/dry run tested | No runtime or model bundled. |

Linux: `./scripts/setup_linux.sh`. Windows PowerShell: `.\scripts\setup_windows.ps1`. Both check Python and use `python -m pip` (the PowerShell script invokes the venv Python explicitly). Run `python -m pytest`, `python -m ruff check .`, `python -m mypy src/baymax`, `baymax --once hello`, and `baymax doctor`.

Required official research gate: read the current `pollen-robotics/reachy_mini` repository and root `AGENTS.md`, Hugging Face Reachy Mini overview/app/simulation pages, and official conversation app. Record source URLs and commit/doc revision for SDK version, supported Python/OS, Wireless architecture, connection/media/motion APIs, simulator command, generated template, packaging metadata, deployment/update/log/stop commands. Reachy 2 material is not an acceptable substitute.

## Phase 7 official-source record (2026-08-08 UTC)

The exact requested source URL was `https://github.com/pollen-robotics/reachy_mini`. A shallow
Git clone failed with `CONNECT tunnel failed, response 403`; the environment's web search for the
same official repository and documentation failed with HTTP 401. Therefore **no source commit,
tag, SDK version, package name, constructor, motion/media API, app metadata, or deployment command
could be verified**. The recorded source revision is consequently `unavailable (network blocked)`,
not a guessed value. All physical connection, audio, movement, and deployment operations remain
fail-closed. Re-run the research gate in a network-enabled environment and record `git rev-parse
HEAD` plus the applicable released tag before replacing any gate.

Implemented in this blocked state: SDK import discovery and metadata-only version reporting,
explicit supervision/checklist configuration, bounded readiness limits, local safe-stop aliases,
redacted diagnostic export, and a readiness UI. These are control-plane safeguards, not a claim of
SDK or physical robot support.
