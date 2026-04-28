param(
  [string]$CasesPath = "C:\ivy\ivy_agent_demo\memory_eval_cases.json",
  [string]$DbPath = "C:\ivy\ivy_agent_demo\memory\ivy_memory.sqlite3",
  [int]$TopK = 5,
  [switch]$BuildSyntheticDb,
  [switch]$CompareLatest,
  [switch]$IngestBeforeEval,
  [string]$RunsRoot = "C:\ivy\runs"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CasesPath)) {
  throw "Cases file not found: $CasesPath"
}

if ($IngestBeforeEval) {
  if (-not (Test-Path -LiteralPath $RunsRoot)) {
    throw "Runs root not found: $RunsRoot"
  }
  python -m ivy_agent_demo.memory_cli --db $DbPath ingest --runs-root $RunsRoot
}

$argsList = @("-m", "ivy_agent_demo.memory_eval", "--cases", $CasesPath, "--top-k", "$TopK")
if (-not $BuildSyntheticDb) {
  $argsList += @("--db", $DbPath)
}
if ($BuildSyntheticDb) {
  $argsList += "--build-synthetic-db"
}
if ($CompareLatest) {
  $argsList += "--compare-latest"
}

python @argsList

$latest = Get-ChildItem -Path "C:\ivy\runs\memory_eval" -Directory -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if ($latest) {
  $report = Join-Path $latest.FullName "memory_eval_report.md"
  Write-Host "Latest memory eval report: $report"
}
