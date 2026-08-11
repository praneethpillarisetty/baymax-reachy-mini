# Local voice model setup

The setup dashboard installs the laptop defaults without enabling them:

* STT: **faster-whisper-small**, from the pinned upstream repository files at
  `https://huggingface.co/Systran/faster-whisper-small/resolve/main/`.
* TTS: **Piper en_US-lessac-medium**, from
  `https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/`.

The authoritative allow-list is `config/voice-models.toml`; directory listings and
browser-provided URLs are never download inputs. Manifest SHA-256 values are checked
when published, and a valid 64-character Hugging Face SHA-256 ETag is also used when
available. Missing upstream checksums do not make installation impossible: exact file
names and URLs remain pinned and a local verification manifest is generated. Partial
downloads use Range, fall back safely when the server returns 200, and remain for Retry;
a checksum mismatch is deleted.

## Download destinations

No asset is written to the checkout. Under `BAYMAX_DATA_DIR` (by default
`~/.local/share/baymax-companion` on Linux and `%LOCALAPPDATA%\BaymaxCompanion`
on Windows), files are stored at:

* `models/voice/faster-whisper-small/`
* `models/voice/piper/en_US-lessac-medium.onnx`
* `models/voice/piper/en_US-lessac-medium.onnx.json`

Install the Python `faster-whisper` runtime and a trusted Piper executable
separately, then enter the Piper executable path in the dashboard. Press Verify
before Activate. Activation is refused until the downloaded manifest hashes
match. The dashboard returns the environment settings to apply on restart; it
does not mutate the running process or silently switch providers:

```text
BAYMAX_ASR_BACKEND=faster-whisper
ASR_MODEL_PATH=<application-data>/models/voice/faster-whisper-small
BAYMAX_TTS_BACKEND=piper
TTS_EXECUTABLE=<configured-piper-executable>
TTS_MODEL_PATH=<application-data>/models/voice/piper/en_US-lessac-medium.onnx
```

Microphone tests request browser permission and enumerate audio inputs. Speaker
tests enumerate outputs and play a short browser-generated tone. Browser
recordings and generated server WAV files use temporary directories and are
deleted immediately after use. Audio is never uploaded to a third party.

Physical Reachy movement remains unavailable: the application continues to
reject the Reachy backend until its supervised adapter validation is complete.
