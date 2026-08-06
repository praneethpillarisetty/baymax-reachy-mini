# Baymax-inspired Reachy Mini companion

A **local-only, simulator-first wellness companion**, not a medical device or clinician. It has a deterministic emergency bypass, allow-listed structured tools, SQLite storage, replaceable mock/Ollama/LiteRT model adapters, console audio, and a hardware-independent robot simulator.

## Quick start

Python 3.10–3.13 is supported by this project. No model is downloaded at startup.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
baymax-companion --once 'hello'
pytest
```

Commands: simulator `baymax-companion`; standalone mock `BAYMAX_LLM_BACKEND=mock baymax-companion`; local-network Ollama `OLLAMA_URL=http://PRIVATE-LAN-IP:11434 BAYMAX_LLM_BACKEND=ollama baymax-companion`; health check `baymax-companion --health-check`; safe stop `baymax-companion --safe-stop`; log collection is application/OS dependent (the prototype writes no remote logs).

> **Research limitation (2026-08-06):** network access to the requested GitHub and Hugging Face official sources returned HTTP 401/403 in this build environment. Therefore no uncertain physical SDK method, package/version claim, media API, simulator CLI, or LiteRT model recommendation is presented as verified. Physical mode deliberately fails closed. Re-run the research checklist in [installation](docs/installation.md) before enabling hardware.

See [architecture](docs/architecture.md), [installation](docs/installation.md), [model selection](docs/model-selection.md), [LiteRT integration](docs/litert-model-integration.md), [Ollama](docs/ollama-setup.md), [deployment](docs/reachy-deployment.md), [safety](docs/healthcare-safety.md), [privacy](docs/privacy.md), and [testing](docs/testing.md).
