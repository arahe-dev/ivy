param(
    [string]$ManifestPath,
    [string]$ExperimentName = "output_test",
    [string]$PromptFile,
    [int]$NPredict = 80,

    # Same baseline parameters
    [string]$ModelPath = "C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf",
    [string]$RuntimePath = "C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe",
    [int]$Port = 8121
)

$ErrorActionPreference = "Stop"

Write-Host "=== Testing n_predict=$NPredict ===" -ForegroundColor Cyan

$serverArgs = @(
    "-m", $ModelPath,
    "--host", "127.0.0.1",
    "--port", $Port,
    "-np", "1",
    "--ctx-size", "8192",
    "--no-webui",
    "--threads", "14",
    "--threads-batch", "14",
    "--flash-attn", "on",
    "--n-gpu-layers", "99",
    "--n-cpu-moe", "16"
)

$runId = (Get-Date).ToString("yyyyMMdd_HHmmss")
$runDir = Join-Path "C:\ivy\ivy\runs\output_test\$ExperimentName" $runId
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$proc = Start-Process -FilePath $RuntimePath -ArgumentList $serverArgs -NoNewWindow -PassThru -RedirectStandardError (Join-Path $runDir "server_err.log")
Start-Sleep -Seconds 5

$prompt = Get-Content $PromptFile -Raw -ErrorAction SilentlyContinue
if (-not $prompt) { 
    $prompt = Get-Content "C:\ivy\ivy\validation_tasks\task1_policy_v3.txt" -Raw 
}

$request = @{
    id_slot = 0
    cache_prompt = $true
    prompt = $prompt
    n_predict = $NPredict
    seed = 12345
    temperature = 0.0
    top_k = 1
    top_p = 1.0
    min_p = 0.0
    repeat_penalty = 1.0
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/completion" -Method Post -Body ($request | ConvertTo-Json -Depth 10) -ContentType "application/json"
$sw.Stop()

Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$t = $resp.timings
$out = @{
    run_id = $runId
    predicted_n = $t.predicted_n
    wall_ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 3)
    ttft_est_ms = [math]::Round($t.prompt_ms + $t.predicted_per_token_ms, 3)
    prompt_n = $t.prompt_n
    decode_tps = [math]::Round($t.predicted_per_second, 3)
    content_len = $resp.content.Length
    coherent = $resp.content.Length -gt 80
}

$out | ConvertTo-Json | Set-Content (Join-Path $runDir "result.json")
$resp.content | Set-Content (Join-Path $runDir "output.txt")

Write-Host "predicted=$($out.predicted_n) wall_ms=$($out.wall_ms) ttft=$($out.ttft_est_ms) decode=$($out.decode_tps)"