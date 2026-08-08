# Troubleshooting

Run `baymax doctor`, or `baymax doctor --json` for machine-readable diagnostics, then `baymax config validate`. A LAN Ollama rejection requires an explicit opt-in and firewall review. An unavailable Ollama model falls back to mock when configured. LiteRT errors name missing profile/model/tokenizer or unsupported architecture. Database errors usually indicate parent-directory permissions. For audio failure, switch to mock/console and inspect device permissions/formats.

Use `baymax config show` to confirm redacted effective settings, `baymax robot-status` without a
connection attempt, and `baymax safe-stop` whenever output should be cancelled. If local voice
preflight fails, retain console/text mode; Baymax never downloads an executable or model.

For model setup, run `baymax models status`. A failed checksum preserves `.partial` for inspection
and retry; cancellation also preserves it. An indeterminate total is honest when the server did not
publish a length. Unverified cards are intentionally blocked. Use `baymax models rollback --yes`
only after reviewing the active and previous configuration. No command deletes a model.

For unexpected motion or daemon/audio loss, stop immediately using the official physical emergency procedure; do not improvise SDK calls. Reachy connection, media, simulator and deployment troubleshooting must use current Reachy Mini—not Reachy 2—documentation.
