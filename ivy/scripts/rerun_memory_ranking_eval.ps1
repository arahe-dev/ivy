param(
  [string]$CasesPath = "ivy_agent_demo\memory_packet_ranking_cases.json",
  [string]$Category = "",
  [switch]$CompareLatest,
  [int]$TopK = 5
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
  $argsList = @(
    "-m", "ivy_agent_demo.memory_ranking_eval",
    "--cases", $CasesPath,
    "--top-k", "$TopK"
  )
  if ($Category -ne "") {
    $argsList += @("--category", $Category)
  }
  if ($CompareLatest) {
    $argsList += "--compare-latest"
  }
  python @argsList

  $latest = Get-ChildItem -Directory "runs\memory_ranking_eval" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($latest) {
    Write-Host "Latest ranking eval report: $($latest.FullName)\ranking_eval_report.md"
  }
} finally {
  Pop-Location
}
