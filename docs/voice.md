# Voice adapters

Mock ASR/TTS and console input/output are dependency-free. `CommandASR` and `CommandTTS` provide real subprocess boundaries around an explicitly installed executable/model and injected microphone/speaker; arguments are configurable rather than assuming a CLI. They never download files and are tested with synthetic WAV audio.

Supported adapter choices are **whisper.cpp tiny.en** (MIT) for a lightweight Raspberry Pi setup, **faster-whisper small** (MIT code; model-card license must also be reviewed) for laptops, and a neutral **Piper** voice (MIT runtime; each voice model card controls its own license) on Raspberry Pi/Linux. Sources and license links are in `config/model-registry.toml`. Kokoro is intentionally not enabled because this project has not verified an official runtime contract. OS/ARM64 builds, model licenses, CLI arguments, latency, and Reachy media integration must be verified locally before publishing a preset. Download/check models explicitly through the selected project's official instructions; startup only calls `check()` and reports missing paths. Raw audio is limited to 30 seconds and 16 MiB, validated as WAV, held in a temporary directory, and not persisted by the adapter. Generated speech is likewise temporary and deleted after playback or failure.

Generic local-command paths are configured with `ASR_EXECUTABLE`, `ASR_MODEL_PATH`, `TTS_EXECUTABLE`, `TTS_MODEL_PATH`, and `TTS_VOICE_ID` (legacy `BAYMAX_` aliases remain accepted). `baymax doctor` fails a selected local backend when either file is absent. No implementation is labeled verified on Reachy Wireless in this checkout: only fake microphone/speaker and subprocess tests have run.

Run `baymax voice-test microphone`, `baymax voice-test speaker`, `baymax voice-test asr`, and `baymax voice-test tts` before enabling a voice loop. Mock/console checks are CI-safe and capture nothing. A selected local adapter fails clearly unless its explicit executable and model paths exist; the application never downloads either and retains no test recording.

The model dashboard lists `faster-whisper-small` and `piper-en-us-lessac-medium` only as unverified
candidates. It does not download or activate them because exact artifact checksums and target
runtime contracts were unavailable. No medical accuracy is claimed. TTS must use a neutral
synthetic voice; cloning Baymax, Scott Adsit, or any actor is prohibited. Wake word remains disabled.

On Windows, after selecting an official artifact URL and published SHA-256, run `.\scripts\download_voice_model.ps1 -Url URL -Sha256 HASH -Output models\voice\MODEL`. Check any local artifact with `python scripts/check_voice_model.py PATH --sha256 HASH`. No default URL is embedded because no cross-platform voice artifact has been verified for both deployment targets.
