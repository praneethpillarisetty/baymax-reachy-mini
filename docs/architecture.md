# Architecture

`src/baymax` is shared, platform-neutral source. Configuration, deterministic safety, orchestration, SQLite, versioned transfer, structured tools, and model/voice/robot protocols import no Windows, Reachy, audio, Ollama-client, or LiteRT package. Optional implementations are selected in the composition root (`cli.py`) by dependency injection.

```text
ASR -> deterministic safety -> orchestrator -> mock/Ollama/LiteRT
                                      |       validated response
                                      v
SQLite <- allow-listed tools <- structured actions -> TTS + robot expression
```

Emergency input bypasses all models. Tool success is reported only after a committed database operation; failures are appended truthfully. Ollama can fall back to an onboard/mock adapter. LiteRT's generic adapter owns metadata and file checks while profile plugins own tokenizer and tensor/signature binding.

The stable model contract exposes `health_check`, structured `generate`, and best-effort `cancel`.
The robot contract exposes connect/start/expression/safe-stop/shutdown and status/capabilities.
Safe-stop sets the robot cancellation gate before cancelling model retries; subsequent expressions
cannot override it. Microphone/ASR and TTS/speaker are injected boundaries, and output failures do
not discard the text response. Requests and structured model output are size/type validated before
local allow-listed tools can run.

Platform targets are intentionally separate: Windows laptop services/package, built-in simulator, Linux ARM64 preflight, and an official Reachy app target awaiting the verified generated template. The simulator allow-lists expressions, supports cancellation and shutdown, and never sends physical movement.
