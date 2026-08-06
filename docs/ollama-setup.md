# Ollama setup

Install Ollama using its current official OS instructions, then explicitly pull the configured model. Keep `OLLAMA_URL=http://127.0.0.1:11434` for same-host use. For enhanced mode, bind only to the private interface, restrict the port to the robot IP in the host firewall, never port-forward it, and deny public/WAN ingress. Configure URL, model, timeout, context, and temperature through environment variables. Confirm with `baymax-companion --health-check`; this checks local application state, not Ollama inference.
