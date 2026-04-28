param(
  [string]$ConfigPath = "C:\ivy\ivy_agent_demo\autoresearch_config.json",
  [string]$ResearchTarget = "",
  [int]$MaxIterations = 3,
  [int]$MaxMinutes = 45,
  [switch]$DryRun,
  [switch]$NoApply
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
  $argsList = @(
    "-m", "ivy_agent_demo.autoresearch",
    "--config", $ConfigPath,
    "--max-iterations", "$MaxIterations",
    "--max-minutes", "$MaxMinutes"
  )
  if ($DryRun) { $argsList += "--dry-run" }
  if ($NoApply) { $argsList += "--no-apply" }
  if (-not [string]::IsNullOrWhiteSpace($ResearchTarget)) {
    $argsList += @("--research-target", $ResearchTarget)
  }
  python @argsList
} finally {
  Pop-Location
}
