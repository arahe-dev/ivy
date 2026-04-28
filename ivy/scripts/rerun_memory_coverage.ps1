param(
  [switch]$AllDefaults,
  [string]$DocsRoot = "ivy\docs",
  [switch]$IncludeSource,
  [ValidateSet("", "safety", "workflow", "runbook")]
  [string]$Category = "",
  [switch]$RunSweepAfter,
  [switch]$CompareLatest
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
  $ingestArgs = @("-m", "ivy_agent_demo.memory_doc_ingest")
  if ($AllDefaults) {
    $ingestArgs += "--all-defaults"
  } else {
    $ingestArgs += @("--docs-root", $DocsRoot)
  }
  if ($IncludeSource) {
    $ingestArgs += "--include-source"
  }

  python @ingestArgs

  $coverageArgs = @("-m", "ivy_agent_demo.memory_coverage_check")
  if ($Category -ne "") {
    $coverageArgs += @("--category", $Category)
  }
  python @coverageArgs

  if ($RunSweepAfter) {
    $sweepArgs = @(
      "-m", "ivy_agent_demo.memory_packet_sweep",
      "--cases", "ivy_agent_demo\memory_packet_eval_real_cases.json",
      "--inspect-failures"
    )
    if ($CompareLatest) {
      $sweepArgs += "--compare-latest"
    }
    python @sweepArgs
  }

  $latest = Get-ChildItem -Directory "runs\memory_coverage" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($latest) {
    Write-Host "Latest coverage report: $($latest.FullName)\coverage_report.md"
  }
} finally {
  Pop-Location
}
