# Testing and benchmark protocol

Run `pytest`, `ruff check .`, `mypy baymax_companion`, and `baymax-companion --once hello`. Tests require no robot, Ollama, LiteRT, microphone, or speaker. Hardware and real-model validation remain outstanding.

`python scripts/benchmark.py MODEL --label NAME` emits a JSON skeleton for file size, startup/CPU/memory and explicit unmeasured fields. For each compact LiteRT candidate, Qwen 4B Ollama baseline, and optional MedGemma laptop experiment, add measured response latency/tokens per second, GPU telemetry, daemon/audio probes, and battery protocol/result. Never infer null measurements.

## Report template

| Model/artifact | Platform | Size | Startup | Peak RAM | Latency | tok/s | CPU/GPU | Daemon | Audio | Battery |
|---|---|---:|---:|---:|---:|---:|---|---|---|---|
| LiteRT compact TBD | Reachy Mini | | | | | | | | | |
| Qwen 3 4B Ollama | laptop | | | | | | | | | |
| MedGemma 4B (research) | laptop | | | | | | | | | |
