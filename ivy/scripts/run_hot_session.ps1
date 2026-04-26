param(
    [Parameter(Mandatory=$true)][string]$ManifestPath,
    [string]$DynamicTask,
    [string]$DynamicTaskFile,
    [int]$SlotId = 0,
    [Parameter(Mandatory=$true)][string]$OutputRunDirectory,
    [int]$PortOverride = 0,
    [switch]$StopServerAfter
)

$ErrorActionPreference = "Stop"

function Read-IvyHotManifest {
    param([string]$Path)

    $manifest = [ordered]@{
        server_args = @()
    }
    $inServerArgs = $false

    foreach ($rawLine in Get-Content -LiteralPath $Path) {
        $line = $rawLine.TrimEnd()
        if ($line.Trim().Length -eq 0 -or $line.TrimStart().StartsWith("#")) {
            continue
        }

        if ($line -match '^server_args:\s*$') {
            $inServerArgs = $true
            continue
        }

        if ($inServerArgs -and $line -match '^\s*-\s*(.*)$') {
            $value = $Matches[1].Trim()
            $value = $value.Trim('"').Trim("'")
            $manifest.server_args += $value
            continue
        }

        $inServerArgs = $false
        if ($line -match '^([^:]+):\s*(.*)$') {
            $key = $Matches[1].Trim()
            $value = $Matches[2].Trim().Trim('"').Trim("'")
            $manifest[$key] = $value
        }
    }

    return $manifest
}

function Convert-ManifestValue {
    param($Value)

    if ($null -eq $Value) { return $null }
    if ($Value -is [string]) {
        if ($Value -match '^(true|false)$') { return [bool]::Parse($Value) }
        if ($Value -match '^-?\d+$') { return [int]$Value }
        if ($Value -match '^-?\d+\.\d+$') { return [double]$Value }
    }
    return $Value
}

function Test-ServerReady {
    param([string]$HostName, [int]$Port)

    try {
        $health = Invoke-WebRequest -Uri "http://$HostName`:$Port/health" -TimeoutSec 2 -UseBasicParsing
        return ($health.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Format-CommandLine {
    param([string]$Exe, [string[]]$CommandArgs)

    return "& `"$Exe`" " + (($CommandArgs | ForEach-Object {
        if ($_ -match '[\s;"]') { '"' + ($_ -replace '"','\"') + '"' } else { $_ }
    }) -join " ")
}

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Manifest not found: $ManifestPath"
}
if ([string]::IsNullOrWhiteSpace($DynamicTask) -and [string]::IsNullOrWhiteSpace($DynamicTaskFile)) {
    throw "Provide -DynamicTask or -DynamicTaskFile"
}
if ($DynamicTask -and $DynamicTaskFile) {
    throw "Provide only one of -DynamicTask or -DynamicTaskFile"
}
if ($DynamicTaskFile) {
    if (-not (Test-Path -LiteralPath $DynamicTaskFile)) {
        throw "Dynamic task file not found: $DynamicTaskFile"
    }
    $DynamicTask = Get-Content -LiteralPath $DynamicTaskFile -Raw
}

$manifest = Read-IvyHotManifest -Path $ManifestPath
$hostName = [string]$manifest.host
$port = [int](Convert-ManifestValue $manifest.port)
if ($PortOverride -gt 0) {
    $port = $PortOverride
}

$serverExe = [string]$manifest.server_exe
$model = [string]$manifest.model
$endpoint = [string]$manifest.endpoint
$staticPrefixPath = [string]$manifest.static_prefix_path
if (-not (Test-Path -LiteralPath $staticPrefixPath)) {
    throw "Static prefix not found: $staticPrefixPath"
}

New-Item -ItemType Directory -Force -Path $OutputRunDirectory | Out-Null

$staticPrefix = Get-Content -LiteralPath $staticPrefixPath -Raw
$fullPrompt = $staticPrefix.TrimEnd() + "`n`nDYNAMIC TASK:`n" + $DynamicTask.Trim()

$serverCommandPath = Join-Path $OutputRunDirectory "server_command.txt"
$requestPath = Join-Path $OutputRunDirectory "request.json"
$responsePath = Join-Path $OutputRunDirectory "response.json"
$outputPath = Join-Path $OutputRunDirectory "output.txt"
$resultPath = Join-Path $OutputRunDirectory "result.json"
$logPath = Join-Path $OutputRunDirectory "hot_session_log.md"
$stdoutPath = Join-Path $OutputRunDirectory "server.stdout.log"
$stderrPath = Join-Path $OutputRunDirectory "server.stderr.log"

$launchedServer = $false
$serverProcess = $null
$serverArgs = @("--model", $model, "--host", $hostName, "--port", "$port") + $manifest.server_args
$serverCommand = Format-CommandLine -Exe $serverExe -CommandArgs $serverArgs

if (Test-ServerReady -HostName $hostName -Port $port) {
    "attached to existing server at http://$hostName`:$port" | Set-Content -LiteralPath $serverCommandPath -Encoding UTF8
} else {
    $serverProcess = Start-Process -FilePath $serverExe -ArgumentList $serverArgs -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -WindowStyle Hidden
    $launchedServer = $true
    $serverCommand | Set-Content -LiteralPath $serverCommandPath -Encoding UTF8

    $ready = $false
    for ($i = 0; $i -lt 240; $i++) {
        if ($serverProcess.HasExited) {
            throw "llama-server exited during startup with code $($serverProcess.ExitCode)"
        }
        if (Test-ServerReady -HostName $hostName -Port $port) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 1000
    }
    if (-not $ready) {
        throw "llama-server did not become ready at http://$hostName`:$port"
    }
}

$bodyObj = [ordered]@{
    id_slot = $SlotId
    cache_prompt = $true
    messages = @(@{
        role = "user"
        content = $fullPrompt
    })
    max_tokens = [int](Convert-ManifestValue $manifest.max_tokens)
    temperature = [double](Convert-ManifestValue $manifest.temperature)
    top_k = [int](Convert-ManifestValue $manifest.top_k)
    top_p = [double](Convert-ManifestValue $manifest.top_p)
    min_p = [double](Convert-ManifestValue $manifest.min_p)
    repeat_penalty = [double](Convert-ManifestValue $manifest.repeat_penalty)
    seed = [int](Convert-ManifestValue $manifest.seed)
    stream = [bool](Convert-ManifestValue $manifest.stream)
}

$body = $bodyObj | ConvertTo-Json -Depth 20
$body | Set-Content -LiteralPath $requestPath -Encoding UTF8

$url = "http://$hostName`:$port$endpoint"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$response = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body -TimeoutSec 600
$sw.Stop()
$response | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $responsePath -Encoding UTF8

$content = [string]$response.choices[0].message.content
$content | Set-Content -LiteralPath $outputPath -Encoding UTF8

$timings = $response.timings
$promptMs = $timings.prompt_ms
$promptN = $timings.prompt_n
$predictedMs = $timings.predicted_ms
$predictedN = $timings.predicted_n
$decodeTps = $null
if ($predictedMs -and $predictedMs -gt 0 -and $predictedN) {
    $decodeTps = [math]::Round(($predictedN * 1000.0 / $predictedMs), 3)
}

$coldPromptN = [int](Convert-ManifestValue $manifest.cold_prompt_n_baseline)
$reuseStatus = "cold_or_lost_reuse"
if (($promptN -ne $null -and $promptN -le 16) -or ($promptMs -ne $null -and $promptMs -lt 150)) {
    $reuseStatus = "likely_hot_reuse"
} elseif ($promptN -ne $null -and $coldPromptN -gt 0 -and $promptN -lt [math]::Round($coldPromptN * 0.85)) {
    $reuseStatus = "partial_reuse"
}

$jsonParseSuccess = $false
try {
    $null = $content | ConvertFrom-Json -ErrorAction Stop
    $jsonParseSuccess = $true
} catch {
    $jsonParseSuccess = $false
}

$notes = @()
if ($launchedServer) {
    $notes += "Started llama-server for this run."
    if (-not $StopServerAfter) {
        $notes += "Server left running for hot-session reuse."
    }
} else {
    $notes += "Attached to an existing live llama-server."
}
if ($reuseStatus -eq "cold_or_lost_reuse") {
    $notes += "Prompt processing looks cold or cache reuse was lost."
} elseif ($reuseStatus -eq "partial_reuse") {
    $notes += "Prompt processing suggests partial prefix reuse."
} else {
    $notes += "Prompt processing suggests hot cache reuse."
}

$serverConfig = [ordered]@{
    server_exe = $serverExe
    host = $hostName
    port = $port
    endpoint = $endpoint
    args = $manifest.server_args
}

$result = [ordered]@{
    model = $model
    server_config = $serverConfig
    slot_id = $SlotId
    prompt_n = $promptN
    predicted_n = $predictedN
    prompt_ms = $promptMs
    wall_ms = [math]::Round($sw.Elapsed.TotalMilliseconds, 1)
    decode_tps = $decodeTps
    cache_reuse_status = $reuseStatus
    has_think_tags = ($content -match "<think>|</think>")
    has_markdown_fence = ($content -match '```')
    json_parse_success = $jsonParseSuccess
    launched_server = $launchedServer
    server_command = $serverCommand
    request_path = $requestPath
    response_path = $responsePath
    output_path = $outputPath
    notes = $notes
}

$result | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $resultPath -Encoding UTF8

$log = @"
# Hot Session Run

- Manifest: `$ManifestPath`
- Attached or launched: $(if ($launchedServer) { "launched" } else { "attached" })
- URL: `$url`
- Slot: `$SlotId`
- Cache prompt: `true`
- Request: `$requestPath`
- Response: `$responsePath`
- Output: `$outputPath`
- Result: `$resultPath`

## Metrics

- prompt_n: `$promptN`
- predicted_n: `$predictedN`
- prompt_ms: `$promptMs`
- wall_ms: `$([math]::Round($sw.Elapsed.TotalMilliseconds, 1))`
- decode_tps: `$decodeTps`
- cache_reuse_status: `$reuseStatus`
- has_think_tags: `$($result.has_think_tags)`
- has_markdown_fence: `$($result.has_markdown_fence)`
- json_parse_success: `$jsonParseSuccess`

## Notes

$($notes | ForEach-Object { "- $_" } | Out-String)
"@
$log | Set-Content -LiteralPath $logPath -Encoding UTF8

if ($StopServerAfter -and $launchedServer -and $serverProcess -and -not $serverProcess.HasExited) {
    Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
    $serverProcess.WaitForExit(10000) | Out-Null
}

$result | ConvertTo-Json -Depth 30
