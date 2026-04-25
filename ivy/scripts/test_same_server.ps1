# Quick 3-repeat cache test on same server
Write-Host "=== 3-repeat to SAME server (layout A) ===" -ForegroundColor Cyan

$serverArgs = @(
    "-m", "C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf",
    "--host", "127.0.0.1",
    "--port", "8121",
    "-np", "1",
    "--ctx-size", "8192",
    "--no-webui",
    "--threads", "14",
    "--threads-batch", "14",
    "--flash-attn", "on",
    "--n-gpu-layers", "99",
    "--n-cpu-moe", "16"
)

$proc = Start-Process -FilePath "C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe" -ArgumentList $serverArgs -NoNewWindow -PassThru -RedirectStandardError "C:\ivy\ivy\runs\same_server_err.log"
Start-Sleep -Seconds 6

$prompt = Get-Content "C:\ivy\ivy\cache_test\layoutA_static1.txt" -Raw

$results = @()
for ($i = 1; $i -le 3; $i++) {
    Write-Host "Request $i..."
    $req = @{
        id_slot = 0
        cache_prompt = $true
        prompt = $prompt
        n_predict = 160
        seed = 12345
        temperature = 0
        top_k = 1
        top_p = 1
        min_p = 0
        repeat_penalty = 1
    } | ConvertTo-Json -Depth 10

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8121/completion" -Method Post -Body $req -ContentType "application/json"
    $sw.Stop()

    $t = $resp.timings
    $ttft = [math]::Round($t.prompt_ms + $t.predicted_per_token_ms, 1)
    $results += @{
        request = $i
        prompt_n = $t.prompt_n
        ttft_est_ms = $ttft
        cached = $resp.tokens_cached
        decode_tps = [math]::Round($t.predicted_per_second, 1)
    }
    Write-Host "  prompt_n=$($t.prompt_n) ttft=${ttft}ms cached=$($resp.tokens_cached)"

    Start-Sleep -Milliseconds 500
}

Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Write-Host "Done" -ForegroundColor Green

$results | Format-Table -AutoSize