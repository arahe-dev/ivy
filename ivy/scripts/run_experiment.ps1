param(
  [string]$ManifestPath,
  [string]$ExperimentName = "custom_experiment",
  [string]$KvPolicyMode,
  [Nullable[int]]$KvCapacityWindows = $null,
  [string]$RunRoot = "C:\\ivy\\ivy\\runs",
  [int]$Port = 0,
  [int]$StartupTimeoutSec = 180,
  [int]$RequestTimeoutSec = 120,

  # Direct parameter mode (used when ManifestPath is not provided)
  [string]$ModelPath,
  [string]$RuntimePath,
  [string]$PromptFile,
  [string]$HostAddr = "127.0.0.1",
  [int]$NParallel = 1,
  [int]$CtxSize = 8192,
  [int]$Threads = 14,
  [int]$ThreadsBatch = 14,
  [string]$FlashAttn = "on",
  [int]$NGpuLayers = 99,
  [int]$NCpuMoe = 16,
  [bool]$NoWebui = $true,
  [int]$Seed = 12345,
  [double]$Temperature = 0.0,
  [int]$TopK = 1,
  [double]$TopP = 1.0,
  [double]$MinP = 0.0,
  [double]$RepeatPenalty = 1.0,
  [int]$NPredict = 160,
  [bool]$CachePrompt = $true
)

$ErrorActionPreference = "Stop"

function New-RunId {
  (Get-Date).ToString("yyyyMMdd_HHmmss")
}

function Parse-Scalar {
  param([string]$Text)

  $v = $Text.Trim()
  if ($v.StartsWith("'") -and $v.EndsWith("'")) { return $v.Substring(1, $v.Length - 2) }
  if ($v.StartsWith('"') -and $v.EndsWith('"')) { return $v.Substring(1, $v.Length - 2) }
  if ($v -eq "true") { return $true }
  if ($v -eq "false") { return $false }
  if ($v -match '^-?\d+$') { return [int]$v }
  if ($v -match '^-?\d+\.\d+$') { return [double]$v }
  return $v
}

function Read-SimpleYaml {
  param([string]$Path)

  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Manifest not found: $Path"
  }

  $root = @{}
  $section = $null
  $lines = Get-Content -LiteralPath $Path
  foreach ($line in $lines) {
    if ($line -match '^\s*$') { continue }
    if ($line -match '^\s*#') { continue }

    if ($line -match '^([A-Za-z0-9_]+):\s*$') {
      $section = $Matches[1]
      if (-not $root.ContainsKey($section)) { $root[$section] = @{} }
      continue
    }

    if ($line -match '^  ([A-Za-z0-9_]+):\s*(.*)$') {
      if (-not $section) { continue }
      $key = $Matches[1]
      $raw = $Matches[2]
      $root[$section][$key] = Parse-Scalar $raw
      continue
    }

    if ($line -match '^([A-Za-z0-9_]+):\s*(.*)$') {
      $key = $Matches[1]
      $raw = $Matches[2]
      $root[$key] = Parse-Scalar $raw
      continue
    }
  }

  return $root
}

function Get-MapValueOrDefault {
  param(
    [hashtable]$Map,
    [string]$Key,
    $DefaultValue
  )
  if ($Map -and $Map.ContainsKey($Key)) { return $Map[$Key] }
  return $DefaultValue
}

function Write-Status {
  param(
    [string]$RunDir,
    [string]$Message
  )
  $line = "[{0}] {1}" -f (Get-Date).ToString("s"), $Message
  Write-Host $line
  Add-Content -Path (Join-Path $RunDir "status.log") -Value $line
}

function Test-TcpPort {
  param(
    [string]$Address,
    [int]$TargetPort,
    [int]$TimeoutMs = 300
  )
  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $async = $client.BeginConnect($Address, $TargetPort, $null, $null)
    if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) { return $false }
    $client.EndConnect($async)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Test-ServerReady {
  param(
    [string]$Address,
    [int]$TargetPort
  )
  try {
    $null = Invoke-RestMethod -Uri ("http://{0}:{1}/slots" -f $Address, $TargetPort) -Method Get -TimeoutSec 3
    return $true
  } catch {
    return $false
  }
}

function Start-Server {
  param(
    [string]$RunDir,
    [string]$ServerExe,
    [string[]]$ServerArgs,
    [string]$ServerHost,
    [int]$ServerPort
  )

  $stdoutPath = Join-Path $RunDir "server_out.log"
  $stderrPath = Join-Path $RunDir "server_err.log"
  New-Item -ItemType File -Force -Path $stdoutPath | Out-Null
  New-Item -ItemType File -Force -Path $stderrPath | Out-Null

  $proc = Start-Process -FilePath $ServerExe -ArgumentList $ServerArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

  $ready = $false
  $deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
  for ($i = 0; (Get-Date) -lt $deadline; $i++) {
    Start-Sleep -Milliseconds 500
    $tcpOpen = Test-TcpPort -Address $ServerHost -TargetPort $ServerPort -TimeoutMs 300
    if ($tcpOpen -and (Test-ServerReady -Address $ServerHost -TargetPort $ServerPort)) {
      $ready = $true
      break
    }
    if ($proc.HasExited) { break }
    if (($i % 10) -eq 0) {
      $tail = ""
      try {
        if (Test-Path -LiteralPath $stderrPath) {
          $tail = (Get-Content -LiteralPath $stderrPath -Tail 1 -ErrorAction SilentlyContinue)
        }
      } catch {}
      if ([string]::IsNullOrWhiteSpace($tail)) {
        if ($tcpOpen) {
          Write-Status -RunDir $RunDir -Message ("port {0} open; waiting for /slots readiness" -f $ServerPort)
        } else {
          Write-Status -RunDir $RunDir -Message ("waiting for server on port {0}" -f $ServerPort)
        }
      } else {
        if ($tcpOpen) {
          Write-Status -RunDir $RunDir -Message ("port {0} open; waiting for /slots readiness; stderr tail: {1}" -f $ServerPort, $tail)
        } else {
          Write-Status -RunDir $RunDir -Message ("waiting for server on port {0}; stderr tail: {1}" -f $ServerPort, $tail)
        }
      }
    }
  }

  if (-not $ready) {
    $exitHint = if ($proc.HasExited) { "process exited with code $($proc.ExitCode)" } else { "process still running" }
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    throw "llama-server failed to become ready on port $ServerPort within ${StartupTimeoutSec}s ($exitHint)"
  }

  return [PSCustomObject]@{
    Proc = $proc
    Stdout = $stdoutPath
    Stderr = $stderrPath
    Args = $ServerArgs
  }
}

function Stop-Server {
  param($ServerObj)
  if ($null -ne $ServerObj -and -not $ServerObj.Proc.HasExited) {
    Stop-Process -Id $ServerObj.Proc.Id -Force
    Start-Sleep -Milliseconds 250
  }
}

function Post-CompletionWithRetry {
  param(
    [string]$ServerHost,
    [int]$ServerPort,
    [hashtable]$Body,
    $Proc,
    [string]$RunDir
  )
  for ($k = 0; $k -lt 3; $k++) {
    try {
      Write-Status -RunDir $RunDir -Message ("POST /completion attempt {0}" -f ($k + 1))
      return Invoke-RestMethod -Uri ("http://{0}:{1}/completion" -f $ServerHost, $ServerPort) -Method Post -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10) -TimeoutSec $RequestTimeoutSec
    } catch {
      if ($Proc.HasExited) { throw "llama-server exited before completion request finished" }
      Write-Status -RunDir $RunDir -Message ("POST /completion attempt {0} failed: {1}" -f ($k + 1), $_.Exception.Message)
      Start-Sleep -Milliseconds 400
      if ($k -eq 2) { throw }
    }
  }
}

function Get-CeilDiv {
  param(
    [int]$Num,
    [int]$Den
  )
  if ($Den -le 0) { throw "Den must be > 0" }
  if ($Num -le 0) { return 0 }
  return [int]([math]::Ceiling($Num / [double]$Den))
}

function Get-KvRegionClassification {
  param(
    [int]$PromptN,
    [int]$PredictedN,
    [int]$WindowSize = 64,
    [int]$PinnedCap = 512,
    [int]$RecentTokens = 512
  )

  $prompt = [math]::Max(0, [int]$PromptN)
  $pred = [math]::Max(0, [int]$PredictedN)
  $total = $prompt + $pred
  $pinned = [math]::Min($PinnedCap, $prompt)
  $recent = [math]::Min($RecentTokens, $total)
  $totalWindows = Get-CeilDiv -Num $total -Den $WindowSize

  $pinnedWindowStart = 0
  $pinnedWindowEnd = (Get-CeilDiv -Num $pinned -Den $WindowSize) - 1
  $recentStartToken = [math]::Max($pinned, $total - $recent)
  $recentWindowStart = Get-CeilDiv -Num $recentStartToken -Den $WindowSize
  $recentWindowEnd = $totalWindows - 1
  $middleWindowStart = $pinnedWindowEnd + 1
  $middleWindowEnd = $recentWindowStart - 1

  $pinnedWindowCount = [math]::Max(0, $pinnedWindowEnd - $pinnedWindowStart + 1)
  $middleWindowCount = [math]::Max(0, $middleWindowEnd - $middleWindowStart + 1)
  $recentWindowCount = [math]::Max(0, $recentWindowEnd - $recentWindowStart + 1)

  $summary = [ordered]@{
    kv_policy_mode = "circular_kv_lite_v0"
    window_size = $WindowSize
    pinned_tokens = $pinned
    recent_tokens = $recent
    total_logical_tokens = $total
    total_windows = $totalWindows
    pinned_windows = $pinnedWindowCount
    middle_windows = $middleWindowCount
    recent_windows = $recentWindowCount
    kv_behavior_changed = $false
  }

  $events = @(
    [ordered]@{
      kv_region = "pinned_prefix"
      window_start = $(if ($pinnedWindowCount -gt 0) { $pinnedWindowStart } else { -1 })
      window_end = $(if ($pinnedWindowCount -gt 0) { $pinnedWindowEnd } else { -1 })
      window_count = $pinnedWindowCount
    },
    [ordered]@{
      kv_region = "middle"
      window_start = $(if ($middleWindowCount -gt 0) { $middleWindowStart } else { -1 })
      window_end = $(if ($middleWindowCount -gt 0) { $middleWindowEnd } else { -1 })
      window_count = $middleWindowCount
    },
    [ordered]@{
      kv_region = "recent"
      window_start = $(if ($recentWindowCount -gt 0) { $recentWindowStart } else { -1 })
      window_end = $(if ($recentWindowCount -gt 0) { $recentWindowEnd } else { -1 })
      window_count = $recentWindowCount
    }
  )

  return [PSCustomObject]@{
    Summary = $summary
    Events = $events
    RegionWindows = [ordered]@{
      pinned = [ordered]@{
        start = $(if ($pinnedWindowCount -gt 0) { $pinnedWindowStart } else { -1 })
        end = $(if ($pinnedWindowCount -gt 0) { $pinnedWindowEnd } else { -1 })
        count = $pinnedWindowCount
      }
      middle = [ordered]@{
        start = $(if ($middleWindowCount -gt 0) { $middleWindowStart } else { -1 })
        end = $(if ($middleWindowCount -gt 0) { $middleWindowEnd } else { -1 })
        count = $middleWindowCount
      }
      recent = [ordered]@{
        start = $(if ($recentWindowCount -gt 0) { $recentWindowStart } else { -1 })
        end = $(if ($recentWindowCount -gt 0) { $recentWindowEnd } else { -1 })
        count = $recentWindowCount
      }
    }
  }
}

function Get-KvPressureSimulation {
  param(
    [hashtable]$KvSummary,
    [hashtable]$RegionWindows,
    [Nullable[int]]$KvCapacityWindows
  )

  $updates = [ordered]@{
    kv_capacity_windows = $KvCapacityWindows
    pressure_detected = $false
    needed_evictions = 0
    simulated_evicted_windows = 0
    fallback_events = 0
    kv_behavior_changed = $false
  }
  $events = @()

  if ($null -eq $KvCapacityWindows) {
    return [PSCustomObject]@{
      SummaryUpdates = $updates
      Events = $events
    }
  }

  $capacity = [math]::Max(0, [int]$KvCapacityWindows)
  $updates.kv_capacity_windows = $capacity

  $totalWindows = [int]$KvSummary.total_windows
  if ($totalWindows -le $capacity) {
    return [PSCustomObject]@{
      SummaryUpdates = $updates
      Events = $events
    }
  }

  $needed = $totalWindows - $capacity
  $updates.pressure_detected = $true
  $updates.needed_evictions = $needed

  $middleCount = [int]$RegionWindows.middle.count
  $middleStart = [int]$RegionWindows.middle.start
  $selected = [math]::Min($needed, $middleCount)
  $updates.simulated_evicted_windows = $selected

  $events += [ordered]@{
    kv_region = "middle"
    kv_action = "would_evict"
    window_start = $(if ($selected -gt 0) { $middleStart } else { -1 })
    window_end = $(if ($selected -gt 0) { $middleStart + $selected - 1 } else { -1 })
    window_count = $selected
    bytes_moved = 0
    notes = "pressure_sim_middle_fifo"
  }

  if ($selected -lt $needed) {
    $updates.fallback_events = 1
    $events += [ordered]@{
      kv_region = "none"
      kv_action = "fallback"
      window_start = -1
      window_end = -1
      window_count = 0
      bytes_moved = 0
      notes = "middle_empty_fallback"
    }
  }

  return [PSCustomObject]@{
    SummaryUpdates = $updates
    Events = $events
  }
}

function Get-SeqRmCapabilityFromLog {
  param(
    [string]$LogText
  )

  if ([string]::IsNullOrWhiteSpace($LogText)) {
    return "unknown"
  }

  if ($LogText -match "common_context_can_seq_rm: the target context does not support partial sequence removal") {
    return "full"
  }

  if ($LogText -match "speculative decoding not supported by this context") {
    return "no"
  }

  return "unknown"
}

function Get-KvPolicyStatus {
  param(
    [string]$KvPolicyMode,
    [string]$SeqRmCapability
  )

  if ($KvPolicyMode -ne "circular_kv_lite_v0") {
    return "observability_only"
  }

  switch ($SeqRmCapability) {
    "part" { return "eligible_for_eviction_prototype" }
    "full" { return "disabled_runtime_not_part_capable" }
    "no" { return "disabled_runtime_not_part_capable" }
    default { return "unknown_runtime_capability" }
  }
}

# --- Resolve config from manifest (if provided) ---
if ($ManifestPath) {
  $m = Read-SimpleYaml -Path $ManifestPath
  $paths = [hashtable](Get-MapValueOrDefault -Map $m -Key "paths" -DefaultValue @{})
  $experiment = [hashtable](Get-MapValueOrDefault -Map $m -Key "experiment" -DefaultValue @{})
  $server = [hashtable](Get-MapValueOrDefault -Map $m -Key "server" -DefaultValue @{})
  $generation = [hashtable](Get-MapValueOrDefault -Map $m -Key "generation" -DefaultValue @{})
  $output = [hashtable](Get-MapValueOrDefault -Map $m -Key "output" -DefaultValue @{})

  $ExperimentName = [string](Get-MapValueOrDefault -Map $m -Key "name" -DefaultValue $ExperimentName)
  $KvPolicyMode = [string](Get-MapValueOrDefault -Map $experiment -Key "policy_mode" -DefaultValue $KvPolicyMode)
  $kvCapacityFromManifest = Get-MapValueOrDefault -Map $experiment -Key "kv_capacity_windows" -DefaultValue $KvCapacityWindows
  if ($null -ne $kvCapacityFromManifest -and "$kvCapacityFromManifest" -ne "") { $KvCapacityWindows = [int]$kvCapacityFromManifest }
  $ModelPath = [string](Get-MapValueOrDefault -Map $paths -Key "model" -DefaultValue $ModelPath)
  $RuntimePath = [string](Get-MapValueOrDefault -Map $paths -Key "runtime" -DefaultValue $RuntimePath)
  $PromptFile = [string](Get-MapValueOrDefault -Map $paths -Key "prompt_file" -DefaultValue $PromptFile)

  $HostAddr = [string](Get-MapValueOrDefault -Map $server -Key "host" -DefaultValue $HostAddr)
  if ($Port -eq 0) { $Port = [int](Get-MapValueOrDefault -Map $server -Key "port" -DefaultValue 8081) }
  $NParallel = [int](Get-MapValueOrDefault -Map $server -Key "n_parallel" -DefaultValue $NParallel)
  $CtxSize = [int](Get-MapValueOrDefault -Map $server -Key "ctx_size" -DefaultValue $CtxSize)
  $Threads = [int](Get-MapValueOrDefault -Map $server -Key "threads" -DefaultValue $Threads)
  $ThreadsBatch = [int](Get-MapValueOrDefault -Map $server -Key "threads_batch" -DefaultValue $ThreadsBatch)
  $FlashAttn = [string](Get-MapValueOrDefault -Map $server -Key "flash_attn" -DefaultValue $FlashAttn)
  $NGpuLayers = [int](Get-MapValueOrDefault -Map $server -Key "n_gpu_layers" -DefaultValue $NGpuLayers)
  $NCpuMoe = [int](Get-MapValueOrDefault -Map $server -Key "n_cpu_moe" -DefaultValue $NCpuMoe)
  $NoWebui = [bool](Get-MapValueOrDefault -Map $server -Key "no_webui" -DefaultValue $NoWebui)

  $Seed = [int](Get-MapValueOrDefault -Map $generation -Key "seed" -DefaultValue $Seed)
  $Temperature = [double](Get-MapValueOrDefault -Map $generation -Key "temperature" -DefaultValue $Temperature)
  $TopK = [int](Get-MapValueOrDefault -Map $generation -Key "top_k" -DefaultValue $TopK)
  $TopP = [double](Get-MapValueOrDefault -Map $generation -Key "top_p" -DefaultValue $TopP)
  $MinP = [double](Get-MapValueOrDefault -Map $generation -Key "min_p" -DefaultValue $MinP)
  $RepeatPenalty = [double](Get-MapValueOrDefault -Map $generation -Key "repeat_penalty" -DefaultValue $RepeatPenalty)
  $NPredict = [int](Get-MapValueOrDefault -Map $generation -Key "n_predict" -DefaultValue $NPredict)
  $CachePrompt = [bool](Get-MapValueOrDefault -Map $generation -Key "cache_prompt" -DefaultValue $CachePrompt)

  $RunRoot = [string](Get-MapValueOrDefault -Map $output -Key "run_root" -DefaultValue $RunRoot)
}

if ($Port -eq 0) { $Port = 8081 }

if (-not $ModelPath) { throw "ModelPath is required (manifest paths.model or -ModelPath)." }
if (-not $RuntimePath) { throw "RuntimePath is required (manifest paths.runtime or -RuntimePath)." }
if (-not $PromptFile) { throw "PromptFile is required (manifest paths.prompt_file or -PromptFile)." }

if (-not (Test-Path -LiteralPath $PromptFile)) { throw "Prompt file not found: $PromptFile" }
if (-not (Test-Path -LiteralPath $RuntimePath)) { throw "Runtime binary not found: $RuntimePath" }
if (-not (Test-Path -LiteralPath $ModelPath)) { throw "Model file not found: $ModelPath" }

$PromptText = (Get-Content -LiteralPath $PromptFile -Raw).ToString()
$runId = New-RunId
$runDir = Join-Path $RunRoot ("{0}\\{1}" -f $ExperimentName, $runId)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
("run_id: {0}`nstarted_local: {1}`n" -f $runId, (Get-Date).ToString("s")) | Set-Content -Path (Join-Path $runDir "run_started.txt")
New-Item -ItemType File -Force -Path (Join-Path $runDir "status.log") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $runDir "notes.md") | Out-Null
Write-Status -RunDir $runDir -Message "run folder initialized"

$serverArgs = @(
  "-m", $ModelPath,
  "--host", $HostAddr,
  "--port", "$Port",
  "-np", "$NParallel",
  "--ctx-size", "$CtxSize",
  "--threads", "$Threads",
  "--threads-batch", "$ThreadsBatch",
  "--n-gpu-layers", "$NGpuLayers",
  "--n-cpu-moe", "$NCpuMoe",
  "--flash-attn", $FlashAttn
)
if ($NoWebui) { $serverArgs += "--no-webui" }

$cmdLine = "& `"$RuntimePath`" " + ($serverArgs -join " ")
$cmdLine | Set-Content -Path (Join-Path $runDir "command.txt")

$request = @{
  id_slot = 0
  cache_prompt = $CachePrompt
  prompt = $PromptText
  n_predict = $NPredict
  seed = $Seed
  temperature = $Temperature
  top_k = $TopK
  top_p = $TopP
  min_p = $MinP
  repeat_penalty = $RepeatPenalty
  stream = $false
}
$request | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "request.json")
Write-Status -RunDir $runDir -Message "command and request artifacts written"

$serverObj = $null
try {
  Write-Status -RunDir $runDir -Message "starting llama-server"
  $serverObj = Start-Server -RunDir $runDir -ServerExe $RuntimePath -ServerArgs $serverArgs -ServerHost $HostAddr -ServerPort $Port
  Write-Status -RunDir $runDir -Message "server ready; running completion"

  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $resp = Post-CompletionWithRetry -ServerHost $HostAddr -ServerPort $Port -Body $request -Proc $serverObj.Proc -RunDir $runDir
  $sw.Stop()
  Write-Status -RunDir $runDir -Message "completion done; writing artifacts"

  $resp | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path $runDir "response.json")
  [string]$resp.content | Set-Content -Path (Join-Path $runDir "output.txt")

  $stderrPath = $serverObj.Stderr
  Stop-Server $serverObj
  $serverObj = $null

  $t = $resp.timings
  $ttftEstMs = [math]::Round(([double]$t.prompt_ms + [double]$t.predicted_per_token_ms), 3)
  $wallMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 3)
  $decodeTps = [math]::Round([double]$t.predicted_per_second, 3)
  $coherent = ([string]$resp.content).Length -gt 120

  $logText = (Get-Content -LiteralPath $stderrPath) -join "`n"
  $cpuBuf = $null
  $cudaBuf = $null
  $seqRmCapability = Get-SeqRmCapabilityFromLog -LogText $logText
  $kvPolicyStatus = Get-KvPolicyStatus -KvPolicyMode $KvPolicyMode -SeqRmCapability $seqRmCapability
  if ($logText -match "CPU_Mapped model buffer size\s*=\s*([0-9\.]+\s+MiB)") { $cpuBuf = $Matches[1] }
  if ($logText -match "CUDA0 model buffer size\s*=\s*([0-9\.]+\s+MiB)") { $cudaBuf = $Matches[1] }

  $result = [ordered]@{
    run_id = $runId
    run_dir = $runDir
    timestamp_local = (Get-Date).ToString("s")
    model = $ModelPath
    runtime = $RuntimePath
    flags = @{
      n_gpu_layers = $NGpuLayers
      n_cpu_moe = $NCpuMoe
      flash_attn = $FlashAttn
      threads = $Threads
      threads_batch = $ThreadsBatch
      ctx_size = $CtxSize
    }
    generation = @{
      seed = $Seed
      temperature = $Temperature
      top_k = $TopK
      top_p = $TopP
      min_p = $MinP
      repeat_penalty = $RepeatPenalty
      n_predict = $NPredict
    }
    kv = @{
      kv_policy_mode = $(if ([string]::IsNullOrWhiteSpace($KvPolicyMode)) { $null } else { $KvPolicyMode })
      seq_rm_capability = $seqRmCapability
      kv_policy_status = $kvPolicyStatus
      kv_behavior_changed = $false
    }
    metrics = @{
      prompt_n = $t.prompt_n
      predicted_n = $t.predicted_n
      ttft_est_ms = $ttftEstMs
      wall_ms = $wallMs
      decode_tps = $decodeTps
      coherent = $coherent
      cpu_mapped_model_buffer = $cpuBuf
      cuda_model_buffer = $cudaBuf
    }
  }

  if ($KvPolicyMode -eq "circular_kv_lite_v0") {
    $promptN = if ($null -ne $t.prompt_n) { [int]$t.prompt_n } else { 0 }
    $predictedN = if ($null -ne $t.predicted_n) { [int]$t.predicted_n } else { 0 }
    $kvClassified = Get-KvRegionClassification -PromptN $promptN -PredictedN $predictedN -WindowSize 64 -PinnedCap 512 -RecentTokens 512
    $result.kv = $kvClassified.Summary
    $result.kv["seq_rm_capability"] = $seqRmCapability
    $result.kv["kv_policy_status"] = $kvPolicyStatus

    $kvTracePath = Join-Path $runDir "kv_trace.jsonl"
    $traceLines = @()
    foreach ($regionEvent in $kvClassified.Events) {
      $kvTraceEvent = [ordered]@{
        run_id = $runId
        kv_policy_mode = "circular_kv_lite_v0"
        kv_region = $regionEvent.kv_region
        kv_action = "retain"
        window_start = $regionEvent.window_start
        window_end = $regionEvent.window_end
        window_count = $regionEvent.window_count
        bytes_moved = 0
        notes = "region_classification_noop"
      }
      $traceLines += ($kvTraceEvent | ConvertTo-Json -Compress)
    }

    $pressure = Get-KvPressureSimulation -KvSummary $kvClassified.Summary -RegionWindows $kvClassified.RegionWindows -KvCapacityWindows $KvCapacityWindows
    foreach ($k in $pressure.SummaryUpdates.Keys) {
      $result.kv[$k] = $pressure.SummaryUpdates[$k]
    }
    foreach ($simEvent in $pressure.Events) {
      $kvTraceEvent = [ordered]@{
        run_id = $runId
        kv_policy_mode = "circular_kv_lite_v0"
        kv_region = $simEvent.kv_region
        kv_action = $simEvent.kv_action
        window_start = $simEvent.window_start
        window_end = $simEvent.window_end
        window_count = $simEvent.window_count
        bytes_moved = 0
        notes = $simEvent.notes
      }
      $traceLines += ($kvTraceEvent | ConvertTo-Json -Compress)
    }

    $traceLines | Set-Content -Path $kvTracePath
    Write-Status -RunDir $runDir -Message "kv_trace.jsonl written for circular_kv_lite_v0 region classification + pressure simulation observability"
  }

  $result | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "result.json")
  Write-Status -RunDir $runDir -Message "result.json written"
} catch {
  $failure = [ordered]@{
    run_id = $runId
    run_dir = $runDir
    timestamp_local = (Get-Date).ToString("s")
    error = $_.Exception.Message
  }
  $failure | ConvertTo-Json -Depth 5 | Set-Content -Path (Join-Path $runDir "failure.json")
  Write-Status -RunDir $runDir -Message ("failed: {0}" -f $_.Exception.Message)
  throw
} finally {
  Stop-Server $serverObj
  Write-Status -RunDir $runDir -Message "server stopped"
}

Write-Output $runDir
