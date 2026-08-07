param(
  [Parameter(Mandatory=$true)][uri]$Url,
  [Parameter(Mandatory=$true)][string]$Sha256,
  [Parameter(Mandatory=$true)][string]$Output
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force (Split-Path -Parent $Output) | Out-Null
Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Output
$Actual = (Get-FileHash -Algorithm SHA256 $Output).Hash.ToLowerInvariant()
if ($Actual -ne $Sha256.ToLowerInvariant()) {
  Remove-Item $Output -Force
  throw "Voice model checksum mismatch; downloaded file was deleted."
}
Write-Host "Verified voice model: $Output"
