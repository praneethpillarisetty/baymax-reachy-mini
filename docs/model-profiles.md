# Model profiles

Copy `config/model-profiles/example.toml` and set `id`, display name, relative model/tokenizer paths, runtime, architecture, quantization, context and target platform. Add exact input/output metadata when inspected. `LiteRTModel(..., dry_run=True)` validates metadata without files; normal mode checks both artifacts. `inspect_signatures()` uses the optional runner or declared metadata. Tokenization and tensor binding belong to a profile-specific plugin implementing the tokenizer/runner protocols; unsupported architectures fail clearly.

Never commit model/tokenizer artifacts. Put them in ignored `models/`, download explicitly, verify hashes/licenses, and benchmark the exact artifact.
