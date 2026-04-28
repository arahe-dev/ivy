param(
  [string]$CasesPath = "C:\ivy\ivy_agent_demo\memory_injection_cases.json",
  [string]$Backends = "ivy_native,mem0",
  [string]$Policy = "",
  [int]$MaxChars = 800,
  [switch]$CompareLatest,
  [switch]$DryRun,
  [switch]$SelfTest
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Push-Location $repoRoot
try {
  $argsList = @(
    "-m", "ivy_agent_demo.memory_backend_compare",
    "--cases", $CasesPath,
    "--backends", $Backends
  )
  if ($Policy -ne "") { $argsList += @("--policy", $Policy) }
  if ($CompareLatest) { $argsList += "--compare-latest" }
  if ($DryRun) { $argsList += "--dry-run" }
  if ($MaxChars -gt 0) { $argsList += @("--max-chars", "$MaxChars") }
  if ($SelfTest) { $argsList += "--self-test" }
  
  python @argsList
  
  if (-not $SelfTest) {
    $latest = Get-ChildItem -Path "C:\ivy\runs\memory_backend_compare" -Directory -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    
    if ($latest) {
      Write-Host ("Latest comparison: {0}" -f $latest.FullName)
      Write-Host ("Report: {0}" -f (Join-Path $latest.FullName "backend_compare_report.md"))
    }
  }
} finally {
  Pop-Location
}