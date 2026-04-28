param(
  [Parameter(Mandatory=$true)][string]$Query,
  [string]$Policy = "hybrid_default",
  [int]$TopK = 5,
  [int]$MaxPacketChars = 1800,
  [string]$DbPath = "C:\ivy\ivy_agent_demo\memory\ivy_memory.sqlite3",
  [switch]$IncludeCandidates,
  [switch]$NoSave
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "-m", "ivy_agent_demo.memory_packet_cli", "preview",
  "--query", $Query,
  "--policy", $Policy,
  "--top-k", "$TopK",
  "--max-packet-chars", "$MaxPacketChars",
  "--db", $DbPath
)
if ($IncludeCandidates) { $argsList += "--include-candidates" }
if ($NoSave) { $argsList += "--no-save" }

python @argsList
