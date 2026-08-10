# Windows laptop installation

Use 64-bit Python 3.10–3.13 in PowerShell: `Set-ExecutionPolicy -Scope Process Bypass; .\scripts\setup_windows.ps1`, then `.\.venv\Scripts\baymax.exe doctor` and `.\.venv\Scripts\baymax.exe --once "hello"`. Data/log/config directories belong under `%LOCALAPPDATA%\BaymaxCompanion`; models are external.

Mock mode works without Ollama. `baymax doctor` reports whether its executable is discoverable and checks `/api/tags` only when Ollama is selected. Windows-to-robot Wi-Fi/USB connection remains unverified until current Reachy Mini OS/SDK documentation is available.

Build on Windows only: `.\scripts\build_windows.ps1`. It runs PyInstaller, creates `dist\BaymaxCompanion.exe`, and executes a mandatory mock-mode smoke test. Compile `deploy\windows\BaymaxCompanion.iss` with a locally installed, reviewed Inno Setup to create `BaymaxCompanion-Setup.exe`. The installer preserves existing user configuration (`onlyifdoesntexist`) and registers uninstall metadata. CI builds and smoke-tests the console executable as a downloadable artifact; no model or Ollama binary is bundled. Inno Setup compilation remains a release-machine step.

## Complete laptop browser conversation setup

Run these commands in **PowerShell**. Ollama, speech recognition, and synthesis stay on the
laptop; Baymax does not send recordings to a cloud API.

```powershell
winget install Ollama.Ollama
ollama serve
ollama pull qwen3:4b
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
$env:BAYMAX_MODE="laptop"
$env:BAYMAX_LLM_BACKEND="ollama"
$env:BAYMAX_FALLBACK_LLM_BACKEND=""
$env:OLLAMA_URL="http://127.0.0.1:11434"
$env:OLLAMA_MODEL="qwen3:4b"
$env:BAYMAX_ASR_BACKEND="mock"
$env:BAYMAX_TTS_BACKEND="console"
baymax config show
baymax doctor
baymax ui
```

Open `http://127.0.0.1:8765`. Type a message and press **Send** (or Enter), then use
**Test Ollama** to verify the attributed backend. **Refresh status** reports Ollama, the
configured model, local speech providers, and simulator status.

For real transcription, install the local package and FFmpeg, download a compatible model
into a directory you control, and configure its path (Baymax never downloads it implicitly):

```powershell
winget install Gyan.FFmpeg
python -m pip install faster-whisper
$env:BAYMAX_ASR_BACKEND="faster-whisper"
$env:ASR_MODEL_PATH="C:\BaymaxModels\faster-whisper-small"
baymax voice-test microphone
```

Restart `baymax ui`, select **Start recording**, grant browser microphone permission, stop
within 30 seconds, review the transcript, and select **Send transcript**. Chrome or Edge
WebM/Opus input requires the FFmpeg codecs bundled with the faster-whisper runtime.

For Piper, download the reviewed Windows Piper release and one reviewed ONNX voice/model
configuration from the official Piper project, then set explicit local paths:

```powershell
$env:BAYMAX_TTS_BACKEND="piper"
$env:TTS_EXECUTABLE="C:\BaymaxTools\piper\piper.exe"
$env:TTS_MODEL_PATH="C:\BaymaxModels\piper\en_US-lessac-medium.onnx"
baymax voice-test speaker
baymax voice-test end-to-end
```

Restart the UI. **Play response** synthesizes a temporary WAV for browser playback;
**Stop playback** stops it and the download link saves the generated WAV. Enable automatic
playback only after a browser user gesture. To test the full loop: record, stop, inspect the
transcript, select **Send transcript**, and play the attributed Ollama response. The robot
remains the simulator and voice input never enables physical movement.

## Phase 7 voice storage and recovery

Voice downloads are stored under `%LOCALAPPDATA%\BaymaxCompanion\models\voice\`, never the checkout. Use the browser's visible error JSON and Retry to resume `.partial` files. Stop Baymax before uninstalling a model directory. Configure a Piper executable only after verifying it is a trusted Windows build with matching architecture.
