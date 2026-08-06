# Platform packaging

One source project produces separate targets. Windows uses the reviewed PyInstaller spec plus optional Inno Setup recipe; models/data/logs/config remain outside the executable and user config survives upgrades. Linux ARM64 uses a wheel embedded in the official Reachy app template—not the Windows executable. Large models are never bundled.

Windows build commands are in `windows-installation.md`. Reachy package/deploy commands cannot be truthfully supplied until the current official template is retrieved. CI builds/tests core behavior without hardware or downloads.
