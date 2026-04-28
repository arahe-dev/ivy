param(
  [string]$CasesPath = "C:\ivy\ivy_agent_demo\memory_packet_eval_real_cases.json",
  [string[]]$Policies = @(),
  [string]$Category = "",
  [switch]$CompareLatest,
  [switch]$InspectFailures,
  [int]$TopK = 5,
  [int]$MaxPacketChars = 1800,
  [string]$DbPath = "C:\ivy\ivy_agent_demo\memory\ivy_memory.sqlite3"
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "-m", "ivy_agent_demo.memory_packet_sweep",
  "--cases", $CasesPath,
  "--db", $DbPath,
  "--top-k", "$TopK",
  "--max-packet-chars", "$MaxPacketChars"
)
if ($CompareLatest) { $argsList += "--compare-latest" }
if ($InspectFailures) { $argsList += "--inspect-failures" }
if (-not [string]::IsNullOrWhiteSpace($Category)) { $argsList += @("--category", $Category) }
if ($Policies.Count -gt 0) {
  $argsList += "--policies"
  $argsList += $Policies
}

python @argsList

$latest = Get-ChildItem -Path "C:\ivy\runs\memory_packet_sweep" -Directory -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if ($latest) {
  Write-Host ("Latest memory packet sweep report: {0}" -f (Join-Path $latest.FullName "sweep_report.md"))
}
