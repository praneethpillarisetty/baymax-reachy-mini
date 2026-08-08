param(
  [ValidateSet("auto", "laptop", "raspberry-pi")][string]$Target = "auto",
  [switch]$Interactive,
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Arguments = @("scripts/setup_models.py", "--target", $Target)
if ($Interactive) { $Arguments += "--interactive" }
elseif ($DryRun) { $Arguments += "--dry-run" }
else { throw "Use -Interactive or -DryRun; hidden downloads are forbidden." }
python @Arguments
