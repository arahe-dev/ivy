param(
    [string]$ManifestPath,
    [string]$ExperimentName = "cache_test",
    [string[]]$PromptFiles,
    [int]$NumRepeats = 3,
    [int]$Port = 8121,

    # Same baseline parameters
    [string]$ModelPath = "C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf",
    [string]$RuntimePath = "C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe",
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

function New-RunId { (Get-Date).ToString("yyyyMMdd_HHmmss") }

$runId = New-RunId
$runDir = Join-Path "C:\ivy\ivy\runs\cache_test\$ExperimentName" $runId
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

Write-Host "[$runId] Starting cache test: $ExperimentName" -ForegroundColor Cyan

# Build server startup args (NO extra flags for now)
$serverArgs = @(
    "-m", $ModelPath,
    "--host", "127.0.0.1",
    "--port", $Port,
    "-np", "1",
    "--ctx-size", $CtxSize,
    "--no-webui",
    "--threads", $Threads,
    "--threads-batch", $ThreadsBatch,
    "--flash-attn", $FlashAttn,
    "--n-gpu-layers", $NGpuLayers,
    "--n-cpu-moe", $NCpuMoe
)

$cmdLine = "& `"$RuntimePath`" " + ($serverArgs -join " ")
$cmdLine | Set-Content -Path (Join-Path $runDir "command.txt")

Write-Host "[$runId] Starting llama-server" -ForegroundColor Yellow

$serverProc = Start-Process -FilePath $RuntimePath -ArgumentList $serverArgs -NoNewWindow -PassThru -RedirectStandardError (Join-Path $runDir "server_err.log")
Start-Sleep -Seconds 5

# Wait for server to be ready
$maxWait = 30
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-RestMethod "http://127.0.0.1:$Port/slots" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($r) { break }
    } catch { }
    Start-Sleep -Seconds 1
    $waited++
}

Write-Host "[$runId] Server ready after ${waited}s"

# Run each prompt file multiple times on SAME server (same id_slot for cache)
$results = @()

foreach ($pf in $PromptFiles) {
    $pfName = [System.IO.Path]::GetFileNameWithoutExtension($pf)

    Write-Host "[$runId] Testing prompt: $pfName" -ForegroundColor Green

    $PromptText = Get-Content -Path $pf -Raw

    for ($i = 0; $i -lt $NumRepeats; $i++) {
        Write-Host "  Try $i..."

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

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/completion" -Method Post -Body ($request | ConvertTo-Json -Depth 10) -ContentType "application/json"
        } catch {
            Write-Host "    ERROR: $_" -ForegroundColor Red
            continue
        }
        $sw.Stop()

        $t = $resp.timings
        $ttftEstMs = [math]::Round(([double]$t.prompt_ms + [double]$t.predicted_per_token_ms), 3)
        $wallMs = [math]::Round($sw.Elapsed.TotalMilliseconds, 3)
        $decodeTps = [math]::Round([double]$t.predicted_per_second, 3)
        $promptN = [int]$t.prompt_n
        $predictedN = [int]$t.predicted_n
        $tokensCached = [int]$resp.tokens_cached
        $coherent = ([string]$resp.content).Length -gt 120

        $results += @{
            run_id = $runId
            prompt_file = $pfName
            repeat = $i
            prompt_n = $promptN
            predicted_n = $predictedN
            ttft_est_ms = $ttftEstMs
            wall_ms = $wallMs
            decode_tps = $decodeTps
            tokens_cached = $tokensCached
            coherent = $coherent
        }

        Write-Host "    prompt_n=$promptN ttft=${ttftEstMs}ms decode=${decodeTps}tps cached=$tokensCached" -ForegroundColor Gray

        Start-Sleep -Milliseconds 500
    }
}

Write-Host "[$runId] Stopping server"
Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# Write results
$results | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $runDir "results.json")

Write-Host "[$runId] Results written to $runDir"
Write-Host "[$runId] Done" -ForegroundColor Green

$results | Format-Table -AutoSize