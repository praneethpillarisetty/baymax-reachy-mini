# Ollama laptop mode

Install Ollama from its current official installer. This repository deliberately does not execute a remote installation script. In PowerShell, run the exact local setup flow:

```powershell
ollama --version
ollama pull qwen3:4b
$env:BAYMAX_MODE='laptop'
$env:BAYMAX_LLM_BACKEND='ollama'
$env:OLLAMA_URL='http://127.0.0.1:11434'
$env:OLLAMA_MODEL='qwen3:4b'
baymax doctor
baymax ui
```

The model name is an example, not a guarantee. The adapter calls `/api/tags` for health/model discovery and `/api/chat` for generation, with configurable timeout, context, temperature and bounded retries. Default URL is `http://127.0.0.1:11434`. A private-LAN URL is rejected unless `BAYMAX_ALLOW_OLLAMA_LAN=true`; firewall it to the robot's address, do not forward the port, and deny WAN/public profiles.
