# Architecture

Input passes through an ASR adapter, deterministic safety engine, conversation orchestrator, replaceable model adapter, schema validation, allow-listed tool executor, TTS adapter, and robot adapter. Emergency input bypasses the model. Tool results—not model claims—are appended to responses. Ollama failures can fall back to a separately configured model. LiteRT tokenization and tensor binding belong in a profile-specific runner; the generic adapter assumes no tensor name, shape, signature, or tokenizer.

The simulator records only allow-listed expressions and supports cancellation and safe shutdown. Physical support is fail-closed and remains unverified.
