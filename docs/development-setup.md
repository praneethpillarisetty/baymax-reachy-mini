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
