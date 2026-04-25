# Test hot-server cache reuse
$ErrorActionPreference = "Continue"

$base = "C:\ivy\ivy\validation_tasks"
$prompts = @("task1_policy_v7.txt","task2_troubleshoot_v7.txt","task1_policy_v7.txt")

$serverArgs = @("-m", "C:\bread_v2\gguf\Qwen3.6-35B-A3B-UD-IQ2_XXS.gguf",
    "--host", "127.0.0.1", "--port", "8121", "-np", "1", "--ctx-size", "8192",
    "--no-webui", "--threads", "14", "--threads-batch", "14",
    "--flash-attn", "on", "--n-gpu-layers", "99", "--n-cpu-moe", "16")

$proc = Start-Process "C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe" -ArgumentList $serverArgs -NoNewWindow -PassThru
Start-Sleep 6

$results = @()
for ($i = 0; $i -lt 3; $i++) {
    $prompt = Get-Content "$base\$($prompts[$i])" -Raw
    $req = @{id_slot=0; cache_prompt=$true; prompt=$prompt; n_predict=160; seed=12345; temperature=0; top_k=1; top_p=1; min_p=0; repeat_penalty=1} | ConvertTo-Json -Depth 10
    
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $resp = Invoke-RestMethod "http://127.0.0.1:8121/completion" -Method Post -Body $req -ContentType "application/json"
    $sw.Stop()
    
    $results += @{
        iteration = $i
        prompt_n = $resp.timings.prompt_n
        predicted = $resp.timings.predicted_n
        ttft = [math]::Round($resp.timings.prompt_ms + $resp.timings.predicted_per_token_ms, 1)
        wall = [math]::Round($sw.Elapsed.TotalMilliseconds, 1)
        cached = $resp.tokens_cached
    }
    Write-Host "Iter $($i): P=$($resp.timings.prompt_n) TTFT=$($results[-1].ttft) WALL=$($results[-1].wall) CACHED=$($resp.tokens_cached)"
}

Stop-Process $proc.Id -Force -ErrorAction SilentlyContinue
$results | ConvertTo-Json | Set-Content "C:\ivy\ivy\runs\cache_test_results.json"
$result