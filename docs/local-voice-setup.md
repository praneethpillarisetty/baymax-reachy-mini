# Local voice model setup

The setup dashboard installs the laptop defaults without enabling them:

* STT: **faster-whisper-small**, from the pinned upstream repository files at
  `https://huggingface.co/Systran/faster-whisper-small/resolve/main/`.
* TTS: **Piper en_US-lessac-medium**, from
  `https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/`.

The exact URLs used are exposed by `baymax.voice.setup.STT_URLS` and `TTS_URLS`.
Hugging Face's SHA-256 LFS ETag is required and checked for every file. A response
without a SHA-256 is rejected. Partial downloads use a Range request and remain
available for Retry; a checksum mismatch is deleted.

## Download destinations

No asset is written to the checkout. Under `BAYMAX_DATA_DIR` (by default
`~/.local/share/baymax-companion` on Linux and `%LOCALAPPDATA%\BaymaxCompanion`
on Windows), files are stored at:

* `voice/faster-whisper-small/`
* `voice/piper/en_US-lessac-medium.onnx`
* `voice/piper/en_US-lessac-medium.onnx.json`

Install the Python `faster-whisper` runtime and a trusted Piper executable
separately, then enter the Piper executable path in the dashboard. Press Verify
before Activate. Activation is refused until the downloaded manifest hashes
match. The dashboard returns the environment settings to apply on restart; it
does not mutate the running process or silently switch providers:

```text
BAYMAX_ASR_BACKEND=faster-whisper
ASR_MODEL_PATH=<application-data>/voice/faster-whisper-small
BAYMAX_TTS_BACKEND=piper
TTS_EXECUTABLE=<configured-piper-executable>
TTS_MODEL_PATH=<application-data>/voice/piper/en_US-lessac-medium.onnx
```

Microphone tests request browser permission and enumerate audio inputs. Speaker
tests enumerate outputs and play a short browser-generated tone. Browser
recordings and generated server WAV files use temporary directories and are
deleted immediately after use. Audio is never uploaded to a third party.

Physical Reachy movement remains unavailable: the application continues to
reject the Reachy backend until its supervised adapter validation is complete.
