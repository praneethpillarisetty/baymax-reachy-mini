# Voice adapters

Mock ASR/TTS and console input/output are dependency-free. `CommandASR` and `CommandTTS` provide real subprocess boundaries around an explicitly installed executable/model and injected microphone/speaker; arguments are configurable rather than assuming a Whisper, Piper, or Kokoro CLI. They never download files and are tested with fake audio.

Candidate investigations include whisper.cpp/faster-whisper tiny-class ASR, Piper, and Kokoro, but OS/ARM64 builds, model license, memory, microphone format, CLI arguments, latency and Reachy media integration must be verified before publishing a preset. Download/check models explicitly through the selected project's official instructions; startup only calls `check()` and reports missing paths. Raw audio is held in a temporary directory and not persisted by the adapter.

Generic local-command paths are configured with `ASR_EXECUTABLE`, `ASR_MODEL_PATH`, `TTS_EXECUTABLE`, and `TTS_MODEL_PATH` (legacy `BAYMAX_` aliases remain accepted). `baymax doctor` fails a selected local backend when either file is absent. No implementation is labeled verified on Reachy Wireless in this checkout: only fake microphone/speaker and subprocess tests have run.

Run `baymax voice-test microphone`, `baymax voice-test speaker`, `baymax voice-test asr`, and `baymax voice-test tts` before enabling a voice loop. Mock/console checks are CI-safe and capture nothing. A selected local adapter fails clearly unless its explicit executable and model paths exist; the application never downloads either and retains no test recording.

On Windows, after selecting an official artifact URL and published SHA-256, run `.\scripts\download_voice_model.ps1 -Url URL -Sha256 HASH -Output models\voice\MODEL`. Check any local artifact with `python scripts/check_voice_model.py PATH --sha256 HASH`. No default URL is embedded because no cross-platform voice artifact has been verified for both deployment targets.
