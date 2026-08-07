# Model profiles

Copy `config/model-profiles/example.toml` and set `id`, display name, relative model/tokenizer paths, runtime, architecture, quantization, context and target platform. Add exact input/output metadata when inspected. `LiteRTModel(..., dry_run=True)` validates metadata without files; normal mode checks both artifacts. `inspect_signatures()` uses the optional runner or declared metadata. Tokenization and tensor binding belong to a profile-specific plugin implementing the tokenizer/runner protocols; unsupported architectures fail clearly.

Never commit model/tokenizer artifacts. Put them in ignored `models/`, download explicitly, verify hashes/licenses, and benchmark the exact artifact.

Use `baymax models list` to validate and enumerate the registry. Use `baymax models inspect --profile config/model-profiles/example.toml` for dry-run path and declared-signature inspection without loading a runtime. It does not prove the artifact runs. Benchmark an installed artifact with `python scripts/benchmark_model.py MODEL --label NAME --verified-platform PLATFORM --probe COMMAND...`; the probe is run once for startup and once for latency, and token throughput is calculated only when `--tokens` is supplied.
