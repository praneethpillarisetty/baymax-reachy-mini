# Troubleshooting

Run `baymax doctor`, or `baymax doctor --json` for machine-readable diagnostics, then `baymax config validate`. A LAN Ollama rejection requires an explicit opt-in and firewall review. An unavailable Ollama model falls back to mock when configured. LiteRT errors name missing profile/model/tokenizer or unsupported architecture. Database errors usually indicate parent-directory permissions. For audio failure, switch to mock/console and inspect device permissions/formats.

For unexpected motion or daemon/audio loss, stop immediately using the official physical emergency procedure; do not improvise SDK calls. Reachy connection, media, simulator and deployment troubleshooting must use current Reachy Mini—not Reachy 2—documentation.
