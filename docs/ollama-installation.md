# Ollama laptop mode

Install Ollama from its current official installer. This repository deliberately does not execute a remote installation script. In PowerShell, verify with `ollama --version`, explicitly obtain a chosen model with `.\scripts\download_model.ps1 -Model qwen3:4b`, then run `$env:BAYMAX_MODE='laptop'; $env:BAYMAX_LLM_BACKEND='ollama'; baymax doctor`.

The model name is an example, not a guarantee. The adapter calls `/api/tags` for health/model discovery and `/api/chat` for generation, with configurable timeout, context, temperature and bounded retries. Default URL is `http://127.0.0.1:11434`. A private-LAN URL is rejected unless `BAYMAX_ALLOW_OLLAMA_LAN=true`; firewall it to the robot's address, do not forward the port, and deny WAN/public profiles.
