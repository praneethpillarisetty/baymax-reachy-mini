$ErrorActionPreference = "Stop"
if (-not $IsWindows) { throw "The Windows executable must be built and tested on Windows." }
$Python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Run scripts/setup_windows.ps1 first." }
& $Python -m PyInstaller --noconfirm --clean deploy\windows\BaymaxCompanion.spec
& .\dist\BaymaxCompanion.exe --once "packaging smoke test"
if ($LASTEXITCODE -ne 0) { throw "Mock executable smoke test failed." }
& .\dist\BaymaxCompanion.exe doctor
Write-Host "Console executable: dist\BaymaxCompanion.exe"
Write-Host "Models and Ollama are intentionally not bundled."
if (Get-Command iscc -ErrorAction SilentlyContinue) {
  iscc deploy\windows\BaymaxCompanion.iss
  Write-Host "Installer: dist\BaymaxCompanion-Setup.exe"
} else {
  Write-Warning "Inno Setup is not installed; console executable succeeded but installer was skipped."
}
