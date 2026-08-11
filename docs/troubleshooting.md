# Troubleshooting

Run `baymax doctor`, or `baymax doctor --json` for machine-readable diagnostics, then `baymax config validate`. One-shot conversations report the backend that produced the response and either `Fallback: none` or a bounded fallback reason; use `baymax --once "hello" --json` for the same metadata as JSON. A LAN Ollama rejection requires an explicit opt-in and firewall review. An unavailable or invalidly structured Ollama response falls back to mock when configured without exposing prompts. LiteRT errors name missing profile/model/tokenizer or unsupported architecture. Database errors usually indicate parent-directory permissions. For audio failure, switch to mock/console and inspect device permissions/formats.

Use `baymax config show` to confirm redacted effective settings, `baymax robot-status` without a
connection attempt, and `baymax safe-stop` whenever output should be cancelled. If local voice
preflight fails, retain console/text mode; Baymax never downloads an executable or model.

For model setup, run `baymax models status`. A failed checksum preserves `.partial` for inspection
and retry; cancellation also preserves it. An indeterminate total is honest when the server did not
publish a length. Unverified cards are intentionally blocked. Use `baymax models rollback --yes`
only after reviewing the active and previous configuration. No command deletes a model.

For unexpected motion or daemon/audio loss, stop immediately using the official physical emergency procedure; do not improvise SDK calls. Reachy connection, media, simulator and deployment troubleshooting must use current Reachy Mini—not Reachy 2—documentation.

## Voice download buttons

The Install action requires JSON `Content-Type`, the manifest `model_id`, and `confirm: true`. Poll `/api/voice/progress`; failures include an error code, message, and recovery. Retry preserves valid partial data, while checksum failure deletes unsafe data. Confirm the destination is under the platform application-data `models/voice` directory and export voice diagnostics. Mock ASR and console TTS intentionally provide no real transcription or speech.
