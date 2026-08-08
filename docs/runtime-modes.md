# Runtime modes

All modes use the same safety-first orchestrator. Configuration precedence is built-in defaults,
an optional TOML file (`--config` or `BAYMAX_CONFIG`), an optional `.env` file, then process
environment variables. Inspect the effective redacted configuration with `baymax config show`.

## Simulator (offline default)

```bash
BAYMAX_MODE=simulator BAYMAX_LLM_BACKEND=mock BAYMAX_VOICE_MODE=mock BAYMAX_ROBOT_BACKEND=simulator baymax --once "hello"
baymax doctor
baymax robot-status
baymax ui --no-browser
```

## Laptop with Ollama

Keep Ollama bound to the laptop loopback interface and use:

```bash
BAYMAX_MODE=laptop BAYMAX_LLM_BACKEND=ollama OLLAMA_URL=http://127.0.0.1:11434 OLLAMA_MODEL=qwen3:4b baymax doctor
baymax models list
baymax ui
```

The model identifier is an example and must already be installed. There is no cloud fallback.

## Optional LiteRT boundary

Set `LITERT_MODEL_PATH`, `LITERT_TOKENIZER_PATH`, and a reviewed `LITERT_MODEL_PROFILE`, then run
`baymax models inspect --profile PROFILE`. Inspection is metadata validation, not inference proof.
Generation remains fail-closed until an exact tokenizer, signatures, runtime, and runner are
registered and tested for that artifact.

## Voice, local data, and stop controls

```bash
baymax voice-test microphone
baymax voice-test asr
baymax voice-test tts
baymax export --output profile.zip
baymax import --input profile.zip --settings-output imported.json
baymax data export --output local-data.json
baymax safe-stop
```

`BAYMAX_VOICE_MODE=local` requires explicit `ASR_EXECUTABLE`, `ASR_MODEL_PATH`,
`TTS_EXECUTABLE`, and `TTS_MODEL_PATH`. No recording starts during preflight and temporary audio
is deleted after processing. A voice or robot output failure leaves the text response available.

## Future supervised Reachy mode

```bash
BAYMAX_MODE=reachy BAYMAX_ROBOT_BACKEND=reachy baymax robot-status
baymax robot-smoke --confirm-supervised
baymax safe-stop
```

The smoke command currently fails closed. Do not run it as a claim of motion support: the official
SDK constructor, lifecycle, capabilities, limits, simulator, and emergency-stop contract must first
be verified and implemented from current official sources, then reviewed using the physical robot
checklist.
