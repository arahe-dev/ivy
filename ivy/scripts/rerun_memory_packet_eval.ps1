param(
  [string]$CasesPath = "C:\ivy\ivy_agent_demo\memory_packet_eval_cases.json",
  [string[]]$Policies = @(),
  [switch]$CompareLatest,
  [int]$TopK = 5,
  [int]$MaxPacketChars = 1800
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "-m", "ivy_agent_demo.memory_packet_eval",
  "--cases", $CasesPath,
  "--top-k", "$TopK",
  "--max-packet-chars", "$MaxPacketChars"
)
if ($CompareLatest) { $argsList += "--compare-latest" }
if ($Policies.Count -gt 0) {
  $argsList += "--policies"
  $argsList += $Policies
}

python @argsList

$latest = Get-ChildItem -Path "C:\ivy\runs\memory_packet_eval" -Directory -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1

if ($latest) {
  Write-Host ("Latest memory packet eval report: {0}" -f (Join-Path $latest.FullName "packet_eval_report.md"))
}
