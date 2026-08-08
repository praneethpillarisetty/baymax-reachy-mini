# Local model setup

Open the localhost-only dashboard with `baymax ui`. The Setup and Models sections explain detected
platform, architecture, Python, RAM, disk, audio preflight state, Ollama, LiteRT, Reachy SDK, model
source/license, verification, compatibility, installation state, and honest download progress.

## Safe first run

```bash
baymax models list
baymax models recommend
baymax models plan --target auto
python scripts/setup_models.py --target auto --interactive
```

Windows PowerShell can use
`./scripts/setup_models.ps1 -Target laptop -Interactive`. Raspberry Pi/Linux ARM64 can use
`python scripts/setup_models.py --target raspberry-pi --dry-run` before interactive confirmation.
Dry-run changes nothing. `baymax models install --target TARGET` also changes nothing unless
`--yes` is supplied. Every plan displays official source, license and compatibility information.

Downloads use `.partial` files, request a byte range on retry, verify a registered SHA-256, and
atomically rename only after verification. Pause, resume, cancel, and retry preserve the partial
file; a valid installed artifact is never overwritten. Unknown totals are displayed as
indeterminate. Models are never removed automatically; removal requires a future explicit,
confirmed removal action.

## Registered choices and evidence status

| ID | Role/provider | Source | License/checksum | Status |
|---|---|---|---|---|
| `mock-llm` | LLM/built-in executable | Project source | Project MIT metadata; built-in marker | Verified offline; no download |
| `qwen3-4b-ollama` | LLM/Ollama | `https://ollama.com/library/qwen3:4b` | Qwen3 repository license; checksum unavailable | Unverified here; automatic install/activation blocked |
| `faster-whisper-small` | STT/Hugging Face | `https://huggingface.co/Systran/faster-whisper-small` | Model card; checksum unavailable | Unverified; manual research only |
| `piper-en-us-lessac-medium` | TTS/Hugging Face | `https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/medium` | Piper voices license; checksum unavailable | Unverified; manual research only |
| `openwakeword` | Optional wake word | `https://github.com/dscripka/openWakeWord` | Repository license; checksum unavailable | Unverified and disabled by default |

The official pages could not be retrieved from this environment (documentation search HTTP 401;
direct HTTPS HTTP 403). Names and URLs above are therefore candidates, not recommendations or
verified runtime claims. No external candidate can be downloaded or activated automatically until
its current official metadata, license, exact artifact checksum, runtime, and target behavior are
reviewed and the registry status is deliberately changed. Kokoro and LiteRT inference are omitted
rather than guessed.

## Activation and rollback

```bash
baymax models test mock-llm
baymax models activate --llm mock-llm --yes
baymax models status
baymax models rollback --yes
```

Activation validates role, verified status, installation manifest, and provider test before an
atomic configuration replacement. The previous configuration is backed up; failure leaves it
active. Activation and rollback require confirmation. Unverified models always fail closed.

## Ollama and private LAN

Baymax never installs Ollama. Install it using the current official local installer, then confirm a
model pull only after the registry card is verified. Verification must cover `ollama list`,
`/api/tags`, and one bounded `/api/chat`. Keep `OLLAMA_URL=http://127.0.0.1:11434`. Raspberry Pi use
of laptop Ollama requires explicit LAN opt-in, an address-specific firewall rule, no port
forwarding/public bind, and acceptance that prompts traverse the private network.
