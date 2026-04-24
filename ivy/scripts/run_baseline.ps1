param(
  [string]$RunRoot = "C:\\ivy\\ivy\\runs",
  [int]$Port = 8081,
  [int]$StartupTimeoutSec = 180,
  [int]$RequestTimeoutSec = 120
)

$ErrorActionPreference = "Stop"

# Frozen baseline config (intentionally duplicated from the manifest for clarity and stability)
$ModelPath   = "C:\\bread_v2\\gguf\\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf"
$RuntimePath = "C:\\Users\\arahe\\dev\\llama.cpp\\build\\bin\\Release\\llama-server.exe"
$PromptFile  = "C:\\ivy\\ivy\\prompts\\qwen35_a3b_baseline_prompt.txt"

$HostAddr = "127.0.0.1"
$CtxSize = 8192
$Threads = 14
$ThreadsBatch = 14
$FlashAttn = "on"
$NGpuLayers = 99
$NCpuMoe = 16

$Seed = 12345
$Temperature = 0.0
$TopK = 1
$TopP = 1.0
$MinP = 0.0
$RepeatPenalty = 1.0
$NPredict = 160
$CachePrompt = $true

function New-RunId {
  (Get-Date).ToString("yyyyMMdd_HHmmss")
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
    if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
      return $false
    }
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

function Get-ServerArgs {
  return @(
    "-m", $ModelPath,
    "--host", $HostAddr,
    "--port", "$Port",
    "-np", "1",
    "--ctx-size", "$CtxSize",
    "--no-webui",
    "--threads", "$Threads",
    "--threads-batch", "$ThreadsBatch",
    "--n-gpu-layers", "$NGpuLayers",
    "--n-cpu-moe", "$NCpuMoe",
    "--flash-attn", $FlashAttn
  )
}

function Start-Server {
  param(
    [string]$RunDir,
    [string[]]$ServerArgs
  )

  $stdoutPath = Join-Path $RunDir "server_out.log"
  $stderrPath = Join-Path $RunDir "server_err.log"

  New-Item -ItemType File -Force -Path $stdoutPath | Out-Null
  New-Item -ItemType File -Force -Path $stderrPath | Out-Null

  $proc = Start-Process -FilePath $RuntimePath -ArgumentList $ServerArgs -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath

  $ready = $false
  $deadline = (Get-Date).AddSeconds($StartupTimeoutSec)
  for ($i = 0; (Get-Date) -lt $deadline; $i++) {
    Start-Sleep -Milliseconds 500
    $tcpOpen = Test-TcpPort -Address $HostAddr -TargetPort $Port -TimeoutMs 300
    if ($tcpOpen -and (Test-ServerReady -Address $HostAddr -TargetPort $Port)) {
      $ready = $true
      break
    } else {
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
            Write-Status -RunDir $RunDir -Message ("port {0} is open; waiting for /slots readiness" -f $Port)
          } else {
            Write-Status -RunDir $RunDir -Message ("waiting for server on port {0}" -f $Port)
          }
        } else {
          if ($tcpOpen) {
            Write-Status -RunDir $RunDir -Message ("port {0} is open; waiting for /slots readiness; stderr tail: {1}" -f $Port, $tail)
          } else {
            Write-Status -RunDir $RunDir -Message ("waiting for server on port {0}; stderr tail: {1}" -f $Port, $tail)
          }
        }
      }
    }
  }

  if (-not $ready) {
    $exitHint = if ($proc.HasExited) { "process exited with code $($proc.ExitCode)" } else { "process still running" }
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
    throw "llama-server failed to become ready on port $Port within ${StartupTimeoutSec}s ($exitHint)"
  }

  return [PSCustomObject]@{
    Proc = $proc
    Args = $ServerArgs
    Stdout = $stdoutPath
    Stderr = $stderrPath
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
    [hashtable]$Body,
    $Proc,
    [string]$RunDir
  )

  for ($k = 0; $k -lt 3; $k++) {
    try {
      Write-Status -RunDir $RunDir -Message ("POST /completion attempt {0}" -f ($k + 1))
      return Invoke-RestMethod -Uri ("http://{0}:{1}/completion" -f $HostAddr, $Port) -Method Post -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10) -TimeoutSec $RequestTimeoutSec
    } catch {
      if ($Proc.HasExited) {
        throw "llama-server exited before completion request finished"
      }
      Write-Status -RunDir $RunDir -Message ("POST /completion attempt {0} failed: {1}" -f ($k + 1), $_.Exception.Message)
      Start-Sleep -Milliseconds 400
      if ($k -eq 2) { throw }
    }
  }
}

if (-not (Test-Path -LiteralPath $PromptFile)) {
  throw "Prompt file not found: $PromptFile"
}
$PromptText = (Get-Content -LiteralPath $PromptFile -Raw).ToString()

$runId = New-RunId
$runDir = Join-Path $RunRoot ("qwen35_a3b_4060_baseline\\{0}" -f $runId)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
("run_id: {0}`nstarted_local: {1}`n" -f $runId, (Get-Date).ToString("s")) | Set-Content -Path (Join-Path $runDir "run_started.txt")
New-Item -ItemType File -Force -Path (Join-Path $runDir "status.log") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $runDir "notes.md") | Out-Null
Write-Status -RunDir $runDir -Message "run folder initialized"

$serverArgs = Get-ServerArgs
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
  $serverObj = Start-Server -RunDir $runDir -ServerArgs $serverArgs
  Write-Status -RunDir $runDir -Message "server ready; running completion"

  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $resp = Post-CompletionWithRetry -Body $request -Proc $serverObj.Proc -RunDir $runDir
  $sw.Stop()
  Write-Status -RunDir $runDir -Message "completion done; writing artifacts"

  $resp | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path $runDir "response.json")
  [string]$resp.content | Set-Content -Path (Join-Path $runDir "output.txt")

  # Stop the server before reading redirected logs so stderr is fully flushed to disk.
  $stderrPath = $serverObj.Stderr
  Stop-Server $serverObj
  $serverObj = $null

  $t = $resp.timings
  $ttftEstMs = [math]::Round(([double]$t.prompt_ms + [double]$t.predicted_per_token_ms), 3)
  $wallMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 3)
  $decodeTps = [math]::Round([double]$t.predicted_per_second, 3)
  $coherent = ([string]$resp.content).Length -gt 120

  $errLines = Get-Content -LiteralPath $stderrPath
  $logText = $errLines -join "`n"
  $cpuBuf = $null
  $cudaBuf = $null
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
