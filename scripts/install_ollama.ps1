$ErrorActionPreference = "Stop"
if (Get-Command ollama -ErrorAction SilentlyContinue) { ollama --version; exit 0 }
Write-Error "Ollama was not found. Install it from the current official Ollama Windows installer, then rerun this script. This script intentionally does not download or execute a remote installer."
