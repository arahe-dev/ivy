param(
  [string]$RepoRoot = "C:\ivy",
  [string]$Store = "C:\ivy\MoME-MoCE-Exp\out\context_memory_daemon_store",
  [string]$SourceRoot = "C:\ivy\MoME-MoCE-Exp",
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8768,
  [switch]$NoIngest,
  [switch]$StopAfterWarm
)

$ErrorActionPreference = "Stop"

$PluginScript = Join-Path $RepoRoot "plugins\ivy-context-memory\scripts\ivy_context_memory.py"
$BaseUrl = "http://$HostName`:$Port"
$WarmQueries = @(
  "What did CP28 show about final answer packet formats?",
  "What MCP tools does ivy-context-memory expose?",
  "What is the latest CP42 rebuild policy versus stale memory?",
  "What is today's Bitcoin price?"
)

function Test-Health {
  param([string]$Url)
  try {
    return Invoke-RestMethod -Uri "$Url/health" -TimeoutSec 2
  } catch {
    return $null
  }
}

function Wait-Health {
  param([string]$Url)
  $deadline = (Get-Date).AddSeconds(15)
  do {
    $health = Test-Health -Url $Url
    if ($null -ne $health -and $health.ok) {
      return $health
    }
    Start-Sleep -Milliseconds 200
  } while ((Get-Date) -lt $deadline)
  throw "context memory daemon did not become healthy at $Url"
}

if (-not (Test-Path $PluginScript)) {
  throw "plugin script not found: $PluginScript"
}

$startedByScript = $false
$process = $null
$health = Test-Health -Url $BaseUrl
if ($null -eq $health -or -not $health.ok) {
  $args = @(
    $PluginScript,
    "--store", $Store,
    "serve",
    "--host", $HostName,
    "--port", "$Port"
  )
  $process = Start-Process -FilePath "python" -ArgumentList $args -PassThru -WindowStyle Hidden
  $startedByScript = $true
  $health = Wait-Health -Url $BaseUrl
}

try {
  $ingest = $null
  if (-not $NoIngest) {
    $ingestPayload = @{ source_root = $SourceRoot; build = $true } | ConvertTo-Json -Depth 8
    $ingest = Invoke-RestMethod -Uri "$BaseUrl/ingest" -Method Post -Body $ingestPayload -ContentType "application/json" -TimeoutSec 120
  }

  $warmPayload = @{ queries = $WarmQueries } | ConvertTo-Json -Depth 8
  $warm = Invoke-RestMethod -Uri "$BaseUrl/warm" -Method Post -Body $warmPayload -ContentType "application/json" -TimeoutSec 120
  $status = Invoke-RestMethod -Uri "$BaseUrl/status" -TimeoutSec 15

  $result = [ordered]@{
    ok = $true
    url = $BaseUrl
    store = $Store
    source_root = $SourceRoot
    started_by_script = $startedByScript
    pid = if ($null -ne $process) { $process.Id } else { $null }
    health = $health
    ingest = $ingest
    warm = $warm
    process_caches = $status.process_caches
  }
  $result | ConvertTo-Json -Depth 20
} finally {
  if ($StopAfterWarm -and $startedByScript -and $null -ne $process) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  }
}
