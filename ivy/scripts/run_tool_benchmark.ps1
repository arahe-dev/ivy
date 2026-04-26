param(
    [Parameter(Mandatory=$true)][string]$ManifestPath,
    [string]$RunId = ("run_" + (Get-Date -Format "yyyyMMdd_HHmmss")),
    [int]$RequestTimeoutSec = 180
)

$ErrorActionPreference = "Stop"

function New-ToolTaskText {
    param($Case)

    $tools = ($Case.allowed_tools | ForEach-Object { "- $_" }) -join "`n"
    $schema = $Case.schema | ConvertTo-Json -Depth 20
    return @"
Return ONLY raw JSON. No markdown. No explanation. No thinking.

Available tools:
$tools

Expected schema:
$schema

Task:
$($Case.prompt)
"@
}

function New-RepairTaskText {
    param($Case, [string]$InvalidOutput)

    $schema = $Case.schema | ConvertTo-Json -Depth 20
    return @"
Return ONLY valid raw JSON. No markdown. No explanation. No thinking.

The previous output failed validation.

Original task:
$($Case.prompt)

Invalid output:
$InvalidOutput

Exact required schema:
$schema

Repair the output so it is a single JSON object with the expected tool and valid arguments.
"@
}

function Invoke-Validator {
    param(
        [string]$Validator,
        [string]$OutputPath,
        [string]$SchemaPath,
        [string]$ValidationPath
    )

    & python $Validator --raw-output $OutputPath --raw-output-is-file --schema $SchemaPath --schema-is-file --out $ValidationPath | Out-Null
    return Get-Content -LiteralPath $ValidationPath -Raw | ConvertFrom-Json
}

function Read-RunResult {
    param([string]$Dir)
    return Get-Content -LiteralPath (Join-Path $Dir "result.json") -Raw | ConvertFrom-Json
}

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
$runRoot = Join-Path $manifest.output_root $RunId
New-Item -ItemType Directory -Force -Path $runRoot | Out-Null

$summary = [ordered]@{
    name = $manifest.name
    run_id = $RunId
    manifest_path = $ManifestPath
    hot_session_manifest = $manifest.hot_session_manifest
    output_root = $runRoot
    started_at = (Get-Date).ToString("o")
    cases = @()
}

$caseIndex = 0
foreach ($case in $manifest.cases) {
    $caseIndex++
    $caseTimer = [System.Diagnostics.Stopwatch]::StartNew()
    $caseDirName = "{0:00}_{1}" -f $caseIndex, $case.id
    $caseDir = Join-Path $runRoot $caseDirName
    $rawDir = Join-Path $caseDir "raw"
    $repairDir = Join-Path $caseDir "repair"
    New-Item -ItemType Directory -Force -Path $rawDir | Out-Null

    $schemaPath = Join-Path $caseDir "expected_schema.json"
    $taskPath = Join-Path $caseDir "task.txt"
    $casePath = Join-Path $caseDir "case.json"
    $rawValidationPath = Join-Path $caseDir "raw_validation.json"
    $repairValidationPath = Join-Path $caseDir "repair_validation.json"

    $case | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $casePath -Encoding UTF8
    $case.schema | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $schemaPath -Encoding UTF8
    $taskText = New-ToolTaskText -Case $case
    $taskText | Set-Content -LiteralPath $taskPath -Encoding UTF8

    Write-Host ("[{0:00}/{1}] raw {2}" -f $caseIndex, $manifest.cases.Count, $case.id)
    & "C:\ivy\ivy\scripts\run_hot_session.ps1" `
        -ManifestPath $manifest.hot_session_manifest `
        -DynamicTaskFile $taskPath `
        -SlotId ([int]$manifest.slot_id) `
        -OutputRunDirectory $rawDir `
        -RequestTimeoutSec $RequestTimeoutSec | Out-Null

    $rawResult = Read-RunResult -Dir $rawDir
    $rawOutputPath = Join-Path $rawDir "output.txt"
    $rawValidation = Invoke-Validator -Validator $manifest.validator -OutputPath $rawOutputPath -SchemaPath $schemaPath -ValidationPath $rawValidationPath

    $repairResult = $null
    $repairValidation = $null
    $retryUsed = $false
    if ($rawValidation.retry_recommended) {
        $retryUsed = $true
        Write-Host ("[{0:00}/{1}] repair {2}" -f $caseIndex, $manifest.cases.Count, $case.id)
        New-Item -ItemType Directory -Force -Path $repairDir | Out-Null
        $invalidOutput = Get-Content -LiteralPath $rawOutputPath -Raw
        $repairTaskPath = Join-Path $caseDir "repair_task.txt"
        New-RepairTaskText -Case $case -InvalidOutput $invalidOutput | Set-Content -LiteralPath $repairTaskPath -Encoding UTF8

        & "C:\ivy\ivy\scripts\run_hot_session.ps1" `
            -ManifestPath $manifest.hot_session_manifest `
            -DynamicTaskFile $repairTaskPath `
            -SlotId ([int]$manifest.slot_id) `
            -OutputRunDirectory $repairDir `
            -RequestTimeoutSec $RequestTimeoutSec | Out-Null

        $repairResult = Read-RunResult -Dir $repairDir
        $repairOutputPath = Join-Path $repairDir "output.txt"
        $repairValidation = Invoke-Validator -Validator $manifest.validator -OutputPath $repairOutputPath -SchemaPath $schemaPath -ValidationPath $repairValidationPath
    }

    $finalValidation = if ($repairValidation) { $repairValidation } else { $rawValidation }
    $finalStatus = $finalValidation.status
    $finalPass = ($finalStatus -eq "pass" -or $finalStatus -eq "partial")
    $caseTimer.Stop()
    Write-Host ("[{0:00}/{1}] final={2} raw={3} retry={4} elapsed={5:n1}s" -f $caseIndex, $manifest.cases.Count, $finalStatus, $rawValidation.status, $retryUsed, $caseTimer.Elapsed.TotalSeconds)

    $summary.cases += [ordered]@{
        index = $caseIndex
        id = $case.id
        category = $case.category
        expected_tool = $case.expected_tool
        raw_status = $rawValidation.status
        raw_failures = $rawValidation.failure_taxonomy
        retry_used = $retryUsed
        repair_status = if ($repairValidation) { $repairValidation.status } else { $null }
        repair_failures = if ($repairValidation) { $repairValidation.failure_taxonomy } else { @() }
        final_status = $finalStatus
        final_pass = $finalPass
        raw_prompt_ms = $rawResult.prompt_ms
        raw_wall_ms = $rawResult.wall_ms
        raw_decode_tps = $rawResult.decode_tps
        raw_cache_reuse_status = $rawResult.cache_reuse_status
        raw_prompt_n = $rawResult.prompt_n
        repair_prompt_ms = if ($repairResult) { $repairResult.prompt_ms } else { $null }
        raw_dir = $rawDir
        repair_dir = if ($repairValidation) { $repairDir } else { $null }
        raw_output = (Get-Content -LiteralPath $rawOutputPath -Raw)
        final_parsed_json = $finalValidation.parsed_json
    }
}

$summary.completed_at = (Get-Date).ToString("o")
$summaryPath = Join-Path $runRoot "benchmark_summary.json"
$summary | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

$cases = $summary.cases
$total = $cases.Count
$rawStrict = @($cases | Where-Object { $_.raw_status -eq "pass" }).Count
$cleaned = @($cases | Where-Object { $_.raw_status -eq "partial" }).Count
$retries = @($cases | Where-Object { $_.retry_used }).Count
$repairedPass = @($cases | Where-Object { $_.retry_used -and ($_.repair_status -eq "pass" -or $_.repair_status -eq "partial") }).Count
$finalPass = @($cases | Where-Object { $_.final_pass }).Count
$partial = @($cases | Where-Object { $_.final_status -eq "partial" }).Count
$fail = $total - $finalPass
$avgPrompt = ($cases | Measure-Object -Property raw_prompt_ms -Average).Average
$avgWall = ($cases | Measure-Object -Property raw_wall_ms -Average).Average
$avgDecode = ($cases | Measure-Object -Property raw_decode_tps -Average).Average

$failureTypes = @{}
foreach ($c in $cases) {
    foreach ($f in $c.raw_failures) {
        if (-not $failureTypes.ContainsKey($f)) { $failureTypes[$f] = 0 }
        $failureTypes[$f]++
    }
    foreach ($f in $c.repair_failures) {
        if (-not $failureTypes.ContainsKey($f)) { $failureTypes[$f] = 0 }
        $failureTypes[$f]++
    }
}

$cacheDist = @{}
foreach ($c in $cases) {
    $k = [string]$c.raw_cache_reuse_status
    if (-not $cacheDist.ContainsKey($k)) { $cacheDist[$k] = 0 }
    $cacheDist[$k]++
}

$metrics = [ordered]@{
    total_cases = $total
    raw_strict_pass_rate = [math]::Round($rawStrict / $total, 4)
    cleaned_pass_rate = [math]::Round(($rawStrict + $cleaned) / $total, 4)
    repaired_pass_rate = if ($retries -gt 0) { [math]::Round($repairedPass / $retries, 4) } else { $null }
    final_pass_rate = [math]::Round($finalPass / $total, 4)
    partial_rate = [math]::Round($partial / $total, 4)
    fail_rate = [math]::Round($fail / $total, 4)
    retry_count = $retries
    common_failure_types = $failureTypes.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { [ordered]@{ type = $_.Key; count = $_.Value } }
    avg_prompt_ms = [math]::Round($avgPrompt, 3)
    avg_wall_ms = [math]::Round($avgWall, 3)
    avg_decode_tps = [math]::Round($avgDecode, 3)
    cache_reuse_status_distribution = $cacheDist
}

$metricsPath = Join-Path $runRoot "benchmark_metrics.json"
$metrics | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $metricsPath -Encoding UTF8

[ordered]@{
    summary_path = $summaryPath
    metrics_path = $metricsPath
    metrics = $metrics
} | ConvertTo-Json -Depth 20
