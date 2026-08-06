# Installation and research checklist

## Development

Linux/macOS: create a Python 3.10–3.13 virtual environment and run `pip install -e '.[dev]'`. Windows native support is unverified; use a supported WSL Linux environment until official Reachy Mini documentation is rechecked. Raspberry Pi dependency and architecture compatibility must be verified per wheel before installation.

## Mandatory official-source verification

Before physical integration, read the current `pollen-robotics/reachy_mini` root `AGENTS.md`, SDK README/examples, Hugging Face Reachy Mini app and simulation pages, and official conversation app. Record exact supported Python versions, distribution/import names, app CLI/template, daemon/simulator commands, connection constructor, media APIs, motion limits, platform support, and wireless hardware limits. The source environment blocked those pages (HTTP 401/403), so this repository intentionally does not invent commands.

Do not use Reachy 2 commands: it is a different platform. Install Ollama and LiteRT only through their current official platform instructions. Model downloads are always explicit.
