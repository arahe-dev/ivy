param(
  [string]$CasesPath = "C:\ivy\ivy_agent_demo\memory_injection_cases.json",
  [string]$CaseId = "",
  [string[]]$Policies = @(),
  [int]$MaxCases = 0,
  [switch]$CompareLatest,
  [switch]$DryRun,
  [switch]$StopOnFailure
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
  $argsList = @(
    "-m", "ivy_agent_demo.memory_injection_experiment",
    "--cases", $CasesPath
  )
  if ($CaseId -ne "") { $argsList += @("--case-id", $CaseId) }
  if ($CompareLatest) { $argsList += "--compare-latest" }
  if ($DryRun) { $argsList += "--dry-run" }
  if ($MaxCases -gt 0) { $argsList += @("--max-cases", "$MaxCases") }
  if ($Policies.Count -gt 0) { $argsList += $Policies }
  
  python @argsList
  
  $latest = Get-ChildItem -Path "C:\ivy\runs\memory_injection_experiment" -Directory -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  
  if ($latest) {
    Write-Host ("Latest memory injection experiment: {0}" -f $latest.FullName)
    Write-Host ("Report: {0}" -f (Join-Path $latest.FullName "experiment_report.md"))
  }
} finally {
  Pop-Location
}