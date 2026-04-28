param(
  [string]$ManifestPath = "C:\ivy\ivy\manifests\qwen36_4060_baseline.yaml",
  [string]$OutputRoot = "C:\ivy\runs\qwen36_4060_bench",
  [string]$ModelPath = "",
  [string]$LlamaServerPath = "",
  [int]$MaxRuns = 0,
  [int]$MatrixLimit = 0,
  [switch]$StopServerAfter,
  [switch]$DryRun,
  [int]$StartupTimeoutSec = 240,
  [int]$RequestTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

function Read-SimpleYaml {
  param([string]$Path)
  $data = [ordered]@{}
  $section = ""
  foreach ($raw in Get-Content -LiteralPath $Path) {
    $line = $raw.TrimEnd()
    $trim = $line.Trim()
    if ($trim.Length -eq 0 -or $trim.StartsWith("#")) { continue }
    if ($line -match '^([A-Za-z0-9_]+):\s*$') {
      $section = $Matches[1]
      $data[$section] = [ordered]@{}
      continue
    }
    if ($line -match '^\s+([^:]+):\s*(.*)$' -and $section) {
      $data[$section][$Matches[1].Trim()] = $Matches[2].Trim().Trim('"').Trim("'")
      continue
    }
    if ($line -match '^([^:]+):\s*(.*)$') {
      $data[$Matches[1].Trim()] = $Matches[2].Trim().Trim('"').Trim("'")
    }
  }
  return $data
}

function Convert-Scalar {
  param($Value)
  if ($null -eq $Value) { return $null }
  $s = [string]$Value
  if ($s -match '^(true|false)$') { return [bool]::Parse($s) }
  if ($s -match '^-?\d+$') { return [int]$s }
  if ($s -match '^-?\d+\.\d+$') { return [double]$s }
  return $s
}

function Test-ServerReady {
  param([string]$HostName, [int]$Port)
  try {
    $r = Invoke-WebRequest -Uri "http://$HostName`:$Port/health" -TimeoutSec 2 -UseBasicParsing
    return ($r.StatusCode -eq 200)
  } catch {
    try {
      $null = Invoke-RestMethod -Uri "http://$HostName`:$Port/slots" -TimeoutSec 2
      return $true
    } catch { return $false }
  }
}

function Format-CommandLine {
  param([string]$Exe, [string[]]$CommandArgs)
  $quotedExe = if ($Exe -match "[\s'`]") { "'" + ($Exe -replace "'", "''") + "'" } else { $Exe }
  return "& $quotedExe " + (($CommandArgs | ForEach-Object {
    $arg = [string]$_
    if ($arg -match "[\s'`]") { "'" + ($arg -replace "'", "''") + "'" } else { $arg }
  }) -join " ")
}

function Get-PythonCommand {
  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return [PSCustomObject]@{ Exe = [string]$python.Source; Arg = $null } }
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return [PSCustomObject]@{ Exe = [string]$py.Source; Arg = "-3" } }
  return $null
}

function Start-BenchServer {
  param([string]$RunDir, [string[]]$ServerArgs)
  $stdout = Join-Path $RunDir "server.stdout.log"
  $stderr = Join-Path $RunDir "server.stderr.log"
  New-Item -ItemType File -Force -Path $stdout | Out-Null
  New-Item -ItemType File -Force -Path $stderr | Out-Null
  $proc = Start-Process -FilePath $script:LlamaExe -ArgumentList $ServerArgs -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru -WindowStyle Hidden
  $deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
  while ((Get-Date) -lt $deadline) {
    if ($proc.HasExited) { throw "llama-server exited during startup with code $($proc.ExitCode)" }
    if (Test-ServerReady -HostName $script:HostName -Port $script:Port) {
      return [PSCustomObject]@{ Proc = $proc; Stdout = $stdout; Stderr = $stderr }
    }
    Start-Sleep -Milliseconds 1000
  }
  throw "llama-server did not become ready at http://$script:HostName`:$script:Port within ${StartupTimeoutSec}s"
}

function Stop-BenchServer {
  param($Server)
  if ($Server -and $Server.Proc -and -not $Server.Proc.HasExited) {
    Stop-Process -Id $Server.Proc.Id -Force -ErrorAction SilentlyContinue
    $Server.Proc.WaitForExit(10000) | Out-Null
  }
}

if (-not (Test-Path -LiteralPath $ManifestPath)) { throw "Manifest not found: $ManifestPath" }
$manifest = Read-SimpleYaml -Path $ManifestPath
$paths = $manifest["paths"]
$server = $manifest["server"]
$generation = $manifest["generation"]

$script:Model = if ($ModelPath) { $ModelPath } else { [string]$paths["model"] }
$script:LlamaExe = if ($LlamaServerPath) { $LlamaServerPath } else { [string]$paths["runtime"] }
$script:HostName = [string]$server["host"]
$script:Port = [int](Convert-Scalar $server["port"])

if (-not $DryRun) {
  if ([string]::IsNullOrWhiteSpace($script:Model) -or $script:Model -match 'CHANGE_ME') { throw "Set a real model path in the manifest or pass -ModelPath." }
  if ([string]::IsNullOrWhiteSpace($script:LlamaExe) -or $script:LlamaExe -match 'CHANGE_ME') { throw "Set llama-server path in the manifest or pass -LlamaServerPath." }
  if (-not (Test-Path -LiteralPath $script:Model)) { throw "Model file not found: $script:Model" }
  if (-not (Test-Path -LiteralPath $script:LlamaExe)) { throw "llama-server.exe not found: $script:LlamaExe" }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runRoot = Join-Path $OutputRoot $timestamp
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$prompts = @(
  @{ name = "short_completion"; text = "Write one concise paragraph about why deterministic benchmarks matter."; n_predict = 64 },
  @{ name = "json_tool_call"; text = "Return only valid JSON for a tool call with this schema: {`"tool`":`"search_notes`",`"arguments`":{`"query`":string,`"limit`":integer}}. Use query=`"qwen benchmark`" and limit=3."; n_predict = 96 },
  @{ name = "static_prefix_long"; text = ("You are IVY measuring local inference. Keep this shared prefix stable. " * 80) + "`nNow summarize the measurement goal in five bullet points."; n_predict = 128 }
)

$ctxs = @(512, 1024, 2048)
$caches = @("f16", "q8_0", "q4_0")
$cpuMoeValues = @($false, $true)
$gpuLayers = @(20, 32)
$limit = if ($MaxRuns -gt 0) { $MaxRuns } elseif ($MatrixLimit -gt 0) { $MatrixLimit } else { 0 }

$matrix = @()
foreach ($ctx in $ctxs) {
  foreach ($ck in $caches) {
    foreach ($cv in $caches) {
      foreach ($cpuMoe in $cpuMoeValues) {
        foreach ($ngl in $gpuLayers) {
          foreach ($prompt in $prompts) {
            $matrix += [PSCustomObject]@{ ctx=$ctx; cache_k=$ck; cache_v=$cv; cpu_moe=$cpuMoe; n_gpu_layers=$ngl; prompt=$prompt }
            if ($limit -gt 0 -and $matrix.Count -ge $limit) { break }
          }
          if ($limit -gt 0 -and $matrix.Count -ge $limit) { break }
        }
        if ($limit -gt 0 -and $matrix.Count -ge $limit) { break }
      }
      if ($limit -gt 0 -and $matrix.Count -ge $limit) { break }
    }
    if ($limit -gt 0 -and $matrix.Count -ge $limit) { break }
  }
  if ($limit -gt 0 -and $matrix.Count -ge $limit) { break }
}

@{ manifest=$ManifestPath; dry_run=[bool]$DryRun; matrix_count=$matrix.Count; created=(Get-Date).ToString("s") } |
  ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runRoot "matrix.json") -Encoding UTF8

$i = 0
foreach ($m in $matrix) {
  $i++
  $configName = ("run_{0:000}_ctx{1}_k{2}_v{3}_moe{4}_ngl{5}_{6}" -f $i,$m.ctx,$m.cache_k,$m.cache_v,$m.cpu_moe,$m.n_gpu_layers,$m.prompt.name)
  $runDir = Join-Path $runRoot $configName
  New-Item -ItemType Directory -Force -Path $runDir | Out-Null

  $config = [ordered]@{
    config_name = $configName
    model_path = $script:Model
    llama_server_path = $script:LlamaExe
    host = $script:HostName
    port = $script:Port
    ctx = $m.ctx
    cache_k = $m.cache_k
    cache_v = $m.cache_v
    cpu_moe = $m.cpu_moe
    n_gpu_layers = $m.n_gpu_layers
    prompt_name = $m.prompt.name
  }
  $config | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $runDir "config.json") -Encoding UTF8

  $request = [ordered]@{
    id_slot = 0
    cache_prompt = $true
    prompt = $m.prompt.text
    n_predict = $m.prompt.n_predict
    seed = [int](Convert-Scalar $generation["seed"])
    temperature = [double](Convert-Scalar $generation["temperature"])
    top_k = [int](Convert-Scalar $generation["top_k"])
    top_p = [double](Convert-Scalar $generation["top_p"])
    min_p = [double](Convert-Scalar $generation["min_p"])
    repeat_penalty = [double](Convert-Scalar $generation["repeat_penalty"])
    stream = $false
  }
  $request | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $runDir "request.json") -Encoding UTF8

  $serverArgs = @(
    "--model", $script:Model, "--host", $script:HostName, "--port", "$script:Port",
    "-np", "1", "--ctx-size", "$($m.ctx)", "--no-webui",
    "--n-gpu-layers", "$($m.n_gpu_layers)",
    "--cache-type-k", $m.cache_k, "--cache-type-v", $m.cache_v,
    "--threads", "$([int](Convert-Scalar $server["threads"]))",
    "--threads-batch", "$([int](Convert-Scalar $server["threads_batch"]))"
  )
  if ([string]$server["flash_attn"]) { $serverArgs += @("--flash-attn", [string]$server["flash_attn"]) }
  if ($m.cpu_moe) { $serverArgs += @("--n-cpu-moe", "$([int](Convert-Scalar $server["n_cpu_moe"]))") }
  Format-CommandLine -Exe $script:LlamaExe -CommandArgs $serverArgs | Set-Content -LiteralPath (Join-Path $runDir "server_command.txt") -Encoding UTF8

  if ($DryRun) { continue }

  $serverObj = $null
  try {
    $serverObj = Start-BenchServer -RunDir $runDir -ServerArgs $serverArgs
    $body = $request | ConvertTo-Json -Depth 20
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $response = Invoke-RestMethod -Uri "http://$script:HostName`:$script:Port/completion" -Method Post -ContentType "application/json" -Body $body -TimeoutSec $RequestTimeoutSec
    $sw.Stop()
    $response | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath (Join-Path $runDir "response.json") -Encoding UTF8
    [string]$response.content | Set-Content -LiteralPath (Join-Path $runDir "output.txt") -Encoding UTF8
    @{ http_success=$true; wall_ms=[math]::Round($sw.Elapsed.TotalMilliseconds, 1); completed=(Get-Date).ToString("s") } |
      ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runDir "result.json") -Encoding UTF8
  } catch {
    @{ error=$_.Exception.Message; load_start_failure=$true; failed=(Get-Date).ToString("s") } |
      ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runDir "failure.json") -Encoding UTF8
  } finally {
    if ($StopServerAfter -or $serverObj) { Stop-BenchServer -Server $serverObj }
  }
}

$collector = Join-Path $PSScriptRoot "collect_qwen36_metrics.py"
if (Test-Path -LiteralPath $collector) {
  $pyCmd = Get-PythonCommand
  if ($null -eq $pyCmd) {
    Write-Warning "Python was not found; skipping metrics collection. Run collect_qwen36_metrics.py manually after installing Python."
  } elseif ([string]::IsNullOrWhiteSpace($pyCmd.Arg)) {
    $pythonExe = [string]$pyCmd.Exe
    & $pythonExe $collector $runRoot
    if ($LASTEXITCODE -ne 0) { Write-Warning "Metrics collection failed with python. Run collect_qwen36_metrics.py manually after verifying Python is installed." }
  } else {
    $pythonExe = [string]$pyCmd.Exe
    $pythonArg = [string]$pyCmd.Arg
    & $pythonExe $pythonArg $collector $runRoot
    if ($LASTEXITCODE -ne 0) { Write-Warning "Metrics collection failed with py -3. Run collect_qwen36_metrics.py manually after verifying Python is installed." }
  }
}

Write-Output $runRoot
