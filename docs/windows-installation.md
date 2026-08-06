# Windows laptop installation

Use 64-bit Python 3.10–3.13 in PowerShell: `Set-ExecutionPolicy -Scope Process Bypass; .\scripts\setup_windows.ps1`, then `.\.venv\Scripts\baymax.exe doctor` and `.\.venv\Scripts\baymax.exe --once "hello"`. Data/log/config directories belong under `%LOCALAPPDATA%\BaymaxCompanion`; models are external.

Mock mode works without Ollama. `baymax doctor` reports whether its executable is discoverable and checks `/api/tags` only when Ollama is selected. Windows-to-robot Wi-Fi/USB connection remains unverified until current Reachy Mini OS/SDK documentation is available.

Build on Windows only: `.\scripts\build_windows.ps1`. It runs PyInstaller, creates `dist\BaymaxCompanion.exe`, and executes a mandatory mock-mode smoke test. Compile `deploy\windows\BaymaxCompanion.iss` with a locally installed, reviewed Inno Setup to create `BaymaxCompanion-Setup.exe`. The installer preserves existing user configuration (`onlyifdoesntexist`) and registers uninstall metadata. CI builds and smoke-tests the console executable as a downloadable artifact; no model or Ollama binary is bundled. Inno Setup compilation remains a release-machine step.
