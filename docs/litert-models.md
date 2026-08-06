# LiteRT candidate evaluation

Catalog presence does not establish Raspberry Pi or Reachy compatibility. Evaluate the exact revisions of MiniCPM5-1B, compact Gemma/Gemma 3n variants, Granite 350M, the newest compact LiteRT text-generation entries, and optional laptop-only MedGemma candidates. For every artifact record LiteRT runtime/version, architecture/operator support on Linux ARM64, tokenizer assets, conversion recipe, named signatures/shapes, quantization, file size, measured peak RAM, startup, latency/tok/s, CPU/GPU, daemon/audio responsiveness, and battery protocol.

No winner is claimed because the current catalog could not be fetched and no target measurements exist. Granite 350M's parameter count suggests a resource hypothesis only; it is not compatibility evidence. MedGemma is laptop research, never the onboard default or medical authority. Use `python scripts/benchmark_model.py PATH --label NAME`; null fields must remain null until measured.
