param([Parameter(Mandatory=$true)][string]$Model)
$ErrorActionPreference = "Stop"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { throw "Ollama is not installed" }
ollama pull $Model
