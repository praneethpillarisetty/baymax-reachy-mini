# Platform packaging

One source project produces separate targets. Windows uses the reviewed PyInstaller spec plus optional Inno Setup recipe; models/data/logs/config remain outside the executable and user config survives upgrades. Linux ARM64 uses a wheel embedded in the official Reachy app template—not the Windows executable. Large models are never bundled.

Windows build commands are in `windows-installation.md`. Reachy package/deploy commands cannot be truthfully supplied until the current official template is retrieved. CI builds/tests core behavior without hardware or downloads.

The repository produces `BaymaxCompanion.exe` with PyInstaller and `BaymaxCompanion-Setup.exe` with Inno Setup as distinct Windows-only build steps. These names describe configured outputs, not evidence that a local Linux checkout built them. Models, Ollama, databases, audio, and secrets are excluded from both artifacts.

CI runs `python -m build` for sdist/wheel and has a separate Windows 3.12 PyInstaller artifact job that runs the executable in mock mode. Linux ARM64 remains a Python wheel/app-template target, never a copied `.exe`.
