# Model compatibility

| Profile | LLM | STT | TTS | Status |
|---|---|---|---|---|
| laptop | Ollama qwen3:4b | faster-whisper-small CPU int8 | Lessac medium + matching Piper | Download path implemented; live runtimes user-verified |
| lite | laptop-hosted | laptop-hosted | laptop-hosted | Hardware connection unverified |
| wireless-hybrid | private-LAN laptop Ollama | lightweight only if CM4-verified | ARM64 only if verified | Recommended design, hardware unverified |
| wireless-local-minimal | no 4B default | tiny candidate | smaller voice candidate | Blocked pending CM4 tests |

The versioned authority is `config/voice-models.toml`. Automatic download and activation flags fail closed.
